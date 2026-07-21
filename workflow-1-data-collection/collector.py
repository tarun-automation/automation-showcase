"""Collects records from a public JSON REST API and saves them to disk."""

import argparse
import csv
import json
import logging
import time
from pathlib import Path

import requests

DEFAULT_URL = "https://jsonplaceholder.typicode.com/posts"

logger = logging.getLogger(__name__)


def fetch_data(url, params=None, timeout=10, max_retries=3, backoff_factor=0.5):
    """Fetch JSON data from `url`, retrying transient failures with backoff."""
    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            last_error = error
            logger.warning("Fetch attempt %d/%d failed: %s", attempt + 1, max_retries, error)
            if attempt < max_retries - 1:
                time.sleep(backoff_factor * (2**attempt))
    raise last_error


def save_json(data, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(data, f, indent=2)
    logger.info("Wrote %d records to %s", len(data), output_path)


def save_csv(data, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not data:
        output_path.write_text("")
        logger.info("Wrote 0 records to %s", output_path)
        return
    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)
    logger.info("Wrote %d records to %s", len(data), output_path)


def build_arg_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="API endpoint to collect data from")
    parser.add_argument("--output-dir", default="output", help="Directory to write the collected data to")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output file format")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of records to keep")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    data = fetch_data(args.url)
    if args.limit is not None:
        data = data[: args.limit]

    output_path = Path(args.output_dir) / f"data.{args.format}"
    if args.format == "json":
        save_json(data, output_path)
    else:
        save_csv(data, output_path)


if __name__ == "__main__":
    main()
