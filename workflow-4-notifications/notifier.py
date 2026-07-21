"""Sends a notification built from a text file (e.g. a report) to console, a
local log file, or a webhook (Slack-compatible incoming webhook format).

Designed to consume the output of workflow-3-report-generation, but works on
any plain-text input file.
"""

import argparse
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


def read_text(input_path):
    return Path(input_path).read_text()


def build_message(text, max_length=500):
    text = text.strip()
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + "..."


def send_console(message):
    print(message)
    return True


def send_file(message, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with output_path.open("a") as f:
        f.write(f"[{timestamp}] {message}\n")
    logger.info("Appended notification to %s", output_path)
    return True


def send_webhook(message, webhook_url, timeout=10, max_retries=3, backoff_factor=0.5):
    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.post(webhook_url, json={"text": message}, timeout=timeout)
            response.raise_for_status()
            logger.info("Sent notification to webhook")
            return True
        except requests.RequestException as error:
            last_error = error
            logger.warning("Webhook attempt %d/%d failed: %s", attempt + 1, max_retries, error)
            if attempt < max_retries - 1:
                time.sleep(backoff_factor * (2**attempt))
    raise last_error


def build_arg_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to the text file to build the notification from")
    parser.add_argument("--channel", choices=["console", "file", "webhook"], default="console", help="Where to send the notification")
    parser.add_argument("--output", default="notifications.log", help="Log file path when --channel=file")
    parser.add_argument("--webhook-url", help="Webhook URL when --channel=webhook")
    parser.add_argument("--max-length", type=int, default=500, help="Maximum notification message length")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.channel == "webhook" and not args.webhook_url:
        raise SystemExit("--webhook-url is required when --channel=webhook")

    message = build_message(read_text(args.input), args.max_length)

    if args.channel == "console":
        send_console(message)
    elif args.channel == "file":
        send_file(message, args.output)
    else:
        send_webhook(message, args.webhook_url)


if __name__ == "__main__":
    main()
