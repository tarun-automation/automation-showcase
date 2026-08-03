import json
from unittest.mock import MagicMock, Mock, call, patch

import pytest
import requests

from api_client import APIClient, _parse_link_next

BASE = "https://api.example.com"

POSTS = [
    {"id": 1, "title": "First", "body": "Hello"},
    {"id": 2, "title": "Second", "body": "World"},
]


def _resp(json_data=None, status_code=200, headers=None):
    r = Mock()
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.headers = headers or {}
    if status_code >= 400:
        r.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status_code}", response=r)
    else:
        r.raise_for_status.return_value = None
    return r


# ── Initialisation ────────────────────────────────────────────────────────────

def test_bearer_token_sets_authorization_header():
    client = APIClient(BASE, bearer_token="secret")
    assert client._session.headers["Authorization"] == "Bearer secret"


def test_api_key_sets_x_api_key_header():
    client = APIClient(BASE, api_key="mykey")
    assert client._session.headers["X-Api-Key"] == "mykey"


def test_basic_auth_sets_session_auth():
    client = APIClient(BASE, basic_auth=("user", "pass"))
    assert client._session.auth == ("user", "pass")


def test_multiple_auth_schemes_raises():
    with pytest.raises(ValueError):
        APIClient(BASE, api_key="k", bearer_token="t")


def test_base_url_always_has_trailing_slash():
    assert APIClient("https://example.com").base_url == "https://example.com/"
    assert APIClient("https://example.com/").base_url == "https://example.com/"


# ── Successful CRUD ───────────────────────────────────────────────────────────

@patch("api_client.requests.Session")
def test_get_sends_get_request(MockSession):
    session = MockSession.return_value
    session.request.return_value = _resp(POSTS[0])

    with APIClient(BASE) as client:
        response = client.get("/posts/1")

    session.request.assert_called_once_with("GET", f"{BASE}/posts/1", params=None, timeout=10)
    assert response.json() == POSTS[0]


@patch("api_client.requests.Session")
def test_post_sends_json_payload(MockSession):
    session = MockSession.return_value
    payload = {"title": "New", "body": "Post"}
    session.request.return_value = _resp({**payload, "id": 101})

    with APIClient(BASE) as client:
        response = client.post("/posts", payload)

    session.request.assert_called_once_with("POST", f"{BASE}/posts", json=payload, timeout=10)
    assert response.json()["id"] == 101


@patch("api_client.requests.Session")
def test_put_sends_json_payload(MockSession):
    session = MockSession.return_value
    payload = {"id": 1, "title": "Updated", "body": "Body"}
    session.request.return_value = _resp(payload)

    with APIClient(BASE) as client:
        client.put("/posts/1", payload)

    session.request.assert_called_once_with("PUT", f"{BASE}/posts/1", json=payload, timeout=10)


@patch("api_client.requests.Session")
def test_patch_sends_json_payload(MockSession):
    session = MockSession.return_value
    session.request.return_value = _resp({"id": 1, "title": "Patched"})

    with APIClient(BASE) as client:
        client.patch("/posts/1", {"title": "Patched"})

    session.request.assert_called_once_with("PATCH", f"{BASE}/posts/1", json={"title": "Patched"}, timeout=10)


@patch("api_client.requests.Session")
def test_delete_sends_delete_request(MockSession):
    session = MockSession.return_value
    session.request.return_value = _resp(status_code=204)

    with APIClient(BASE) as client:
        client.delete("/posts/1")

    session.request.assert_called_once_with("DELETE", f"{BASE}/posts/1", timeout=10)


# ── Retry logic ───────────────────────────────────────────────────────────────

@patch("api_client.time.sleep", return_value=None)
@patch("api_client.requests.Session")
def test_retries_on_connection_error_then_succeeds(MockSession, mock_sleep):
    session = MockSession.return_value
    session.request.side_effect = [
        requests.ConnectionError("down"),
        _resp(POSTS[0]),
    ]

    with APIClient(BASE, max_retries=3) as client:
        response = client.get("/posts/1")

    assert response.json() == POSTS[0]
    assert session.request.call_count == 2
    mock_sleep.assert_called_once()


@patch("api_client.time.sleep", return_value=None)
@patch("api_client.requests.Session")
def test_raises_after_exhausting_retries(MockSession, mock_sleep):
    session = MockSession.return_value
    session.request.side_effect = requests.ConnectionError("down")

    with pytest.raises(requests.ConnectionError):
        with APIClient(BASE, max_retries=2) as client:
            client.get("/posts/1")

    assert session.request.call_count == 2


@patch("api_client.time.sleep", return_value=None)
@patch("api_client.requests.Session")
def test_retries_on_500_then_succeeds(MockSession, mock_sleep):
    session = MockSession.return_value
    session.request.side_effect = [
        _resp(status_code=500),
        _resp(POSTS[0]),
    ]

    with APIClient(BASE, max_retries=3) as client:
        response = client.get("/posts/1")

    assert response.json() == POSTS[0]
    assert session.request.call_count == 2


@patch("api_client.time.sleep", return_value=None)
@patch("api_client.requests.Session")
def test_rate_limit_respects_retry_after_header(MockSession, mock_sleep):
    session = MockSession.return_value
    rate_limited = _resp(status_code=429, headers={"Retry-After": "2"})
    rate_limited.raise_for_status.return_value = None
    session.request.side_effect = [rate_limited, _resp(POSTS[0])]

    with APIClient(BASE, max_retries=3) as client:
        response = client.get("/posts/1")

    assert response.json() == POSTS[0]
    mock_sleep.assert_called_once_with(2.0)


@patch("api_client.requests.Session")
def test_raises_on_404(MockSession):
    session = MockSession.return_value
    session.request.return_value = _resp(status_code=404)

    with pytest.raises(requests.HTTPError):
        with APIClient(BASE) as client:
            client.get("/posts/999")


# ── Pagination ────────────────────────────────────────────────────────────────

@patch("api_client.requests.Session")
def test_paginate_yields_all_records_via_page_param(MockSession):
    session = MockSession.return_value
    session.request.side_effect = [
        _resp(POSTS),
        _resp([]),
    ]

    with APIClient(BASE) as client:
        records = list(client.paginate("/posts", page_size=2))

    assert records == POSTS


@patch("api_client.requests.Session")
def test_paginate_follows_link_header(MockSession):
    session = MockSession.return_value
    page1 = _resp(
        [POSTS[0]],
        headers={"Link": f'<{BASE}/posts?page=2>; rel="next"'},
    )
    page2 = _resp([POSTS[1]], headers={})
    session.request.side_effect = [page1, page2, _resp([])]

    with APIClient(BASE) as client:
        records = list(client.paginate("/posts", page_size=1))

    assert records == POSTS


@patch("api_client.requests.Session")
def test_paginate_stops_on_empty_page(MockSession):
    session = MockSession.return_value
    session.request.side_effect = [_resp([])]

    with APIClient(BASE) as client:
        records = list(client.paginate("/posts"))

    assert records == []


# ── Link header parser ────────────────────────────────────────────────────────

def test_parse_link_next_extracts_url():
    header = '<https://api.example.com/posts?page=2>; rel="next", <https://api.example.com/posts?page=5>; rel="last"'
    assert _parse_link_next(header) == "https://api.example.com/posts?page=2"


def test_parse_link_next_returns_none_when_absent():
    header = '<https://api.example.com/posts?page=1>; rel="prev"'
    assert _parse_link_next(header) is None


def test_parse_link_next_returns_none_for_empty_header():
    assert _parse_link_next("") is None


# ── Context manager ───────────────────────────────────────────────────────────

@patch("api_client.requests.Session")
def test_context_manager_closes_session(MockSession):
    session = MockSession.return_value

    with APIClient(BASE):
        pass

    session.close.assert_called_once()
