"""REST API client with authentication, pagination, rate-limit handling, and CRUD helpers."""

import argparse
import json
import logging
import time
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)


class APIClient:
    """Thin wrapper around :class:`requests.Session` for a single base URL.

    Supports three auth modes (mutually exclusive):
      - ``api_key``   — sent as the ``X-Api-Key`` request header
      - ``bearer``    — sent as ``Authorization: Bearer <token>``
      - ``basic``     — ``(username, password)`` tuple for HTTP Basic auth

    All requests share the same session (connection pooling) and default
    timeout.  Transient errors (network failures, 5xx responses) are retried
    with exponential backoff; 429 responses respect the ``Retry-After`` header.
    """

    def __init__(
        self,
        base_url,
        *,
        api_key=None,
        bearer_token=None,
        basic_auth=None,
        timeout=10,
        max_retries=3,
        backoff_factor=0.5,
    ):
        if sum(x is not None for x in (api_key, bearer_token, basic_auth)) > 1:
            raise ValueError("Specify at most one of: api_key, bearer_token, basic_auth")

        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        self._session = requests.Session()
        if api_key:
            self._session.headers["X-Api-Key"] = api_key
        if bearer_token:
            self._session.headers["Authorization"] = f"Bearer {bearer_token}"
        if basic_auth:
            self._session.auth = basic_auth

    def _url(self, path):
        return urljoin(self.base_url, path.lstrip("/"))

    def _request(self, method, path, **kwargs):
        url = self._url(path)
        kwargs.setdefault("timeout", self.timeout)
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = self._session.request(method, url, **kwargs)

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", self.backoff_factor * (2 ** attempt)))
                    logger.warning("Rate limited; retrying in %.1fs (attempt %d/%d)", retry_after, attempt + 1, self.max_retries)
                    time.sleep(retry_after)
                    continue

                if response.status_code >= 500:
                    logger.warning("Server error %d; retrying (attempt %d/%d)", response.status_code, attempt + 1, self.max_retries)
                    last_error = requests.HTTPError(f"Server error {response.status_code}", response=response)
                    time.sleep(self.backoff_factor * (2 ** attempt))
                    continue

                response.raise_for_status()
                return response

            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                logger.warning("Request failed: %s; retrying (attempt %d/%d)", exc, attempt + 1, self.max_retries)
                time.sleep(self.backoff_factor * (2 ** attempt))

        raise last_error or requests.HTTPError("Max retries exceeded")

    # ── CRUD helpers ──────────────────────────────────────────────────────────

    def get(self, path, params=None):
        return self._request("GET", path, params=params)

    def post(self, path, payload):
        return self._request("POST", path, json=payload)

    def put(self, path, payload):
        return self._request("PUT", path, json=payload)

    def patch(self, path, payload):
        return self._request("PATCH", path, json=payload)

    def delete(self, path):
        return self._request("DELETE", path)

    # ── Pagination ────────────────────────────────────────────────────────────

    def paginate(self, path, params=None, page_param="page", page_size_param="_limit", page_size=10):
        """Yield individual records from a paginated endpoint.

        Tries ``Link`` header pagination first (RFC 5988 ``rel="next"``).
        Falls back to incrementing ``page`` query parameter until an empty
        page is returned.
        """
        params = dict(params or {})
        params.setdefault(page_size_param, page_size)

        response = self.get(path, params=params)
        while True:
            records = response.json()
            if not records:
                break
            yield from records

            next_url = _parse_link_next(response.headers.get("Link", ""))
            if next_url:
                response = self._request("GET", next_url)
            else:
                current_page = int(params.get(page_param, 1))
                params[page_param] = current_page + 1
                response = self.get(path, params=params)
                if not response.json():
                    break

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _parse_link_next(link_header):
    """Extract the URL for rel="next" from an RFC 5988 Link header."""
    for part in link_header.split(","):
        url_part, *params = [p.strip() for p in part.split(";")]
        if any(p.strip() == 'rel="next"' for p in params):
            return url_part.strip("<>")
    return None


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_arg_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://jsonplaceholder.typicode.com", help="API base URL")
    parser.add_argument("--bearer-token", default=None, help="Bearer token for Authorization header")
    parser.add_argument("--api-key", default=None, help="API key sent as X-Api-Key header")
    subparsers = parser.add_subparsers(dest="command", required=True)

    get_p = subparsers.add_parser("get", help="Fetch a single resource")
    get_p.add_argument("path", help="Resource path, e.g. /posts/1")

    list_p = subparsers.add_parser("list", help="List resources (with pagination)")
    list_p.add_argument("path", help="Collection path, e.g. /posts")
    list_p.add_argument("--limit", type=int, default=10, help="Page size")

    create_p = subparsers.add_parser("create", help="Create a resource (POST)")
    create_p.add_argument("path", help="Collection path, e.g. /posts")
    create_p.add_argument("--data", required=True, help="JSON string payload")

    update_p = subparsers.add_parser("update", help="Replace a resource (PUT)")
    update_p.add_argument("path", help="Resource path, e.g. /posts/1")
    update_p.add_argument("--data", required=True, help="JSON string payload")

    delete_p = subparsers.add_parser("delete", help="Delete a resource")
    delete_p.add_argument("path", help="Resource path, e.g. /posts/1")

    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    client = APIClient(
        args.base_url,
        bearer_token=getattr(args, "bearer_token", None),
        api_key=getattr(args, "api_key", None),
    )

    with client:
        if args.command == "get":
            result = client.get(args.path).json()
            print(json.dumps(result, indent=2))

        elif args.command == "list":
            records = list(client.paginate(args.path, page_size=args.limit))
            print(json.dumps(records, indent=2))
            logger.info("Fetched %d records", len(records))

        elif args.command == "create":
            payload = json.loads(args.data)
            result = client.post(args.path, payload).json()
            print(json.dumps(result, indent=2))

        elif args.command == "update":
            payload = json.loads(args.data)
            result = client.put(args.path, payload).json()
            print(json.dumps(result, indent=2))

        elif args.command == "delete":
            client.delete(args.path)
            print(f"Deleted {args.path}")


if __name__ == "__main__":
    main()
