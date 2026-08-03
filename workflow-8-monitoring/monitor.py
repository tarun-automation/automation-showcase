"""Polls HTTP endpoints and writes an availability/latency report."""

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

UP   = "up"
DOWN = "down"


def _now():
    return datetime.now(timezone.utc).isoformat()


def check_endpoint(url, *, timeout=10, expected_status=200):
    """Probe `url` once and return a result dict."""
    start = time.monotonic()
    try:
        resp = requests.get(url, timeout=timeout, allow_redirects=True)
        latency = round((time.monotonic() - start) * 1000, 1)
        status = UP if resp.status_code == expected_status else DOWN
        return {"url": url, "status": status, "http_status": resp.status_code,
                "latency_ms": latency, "error": None, "checked_at": _now()}
    except requests.RequestException as exc:
        latency = round((time.monotonic() - start) * 1000, 1)
        logger.warning("Check failed for %s: %s", url, exc)
        return {"url": url, "status": DOWN, "http_status": None,
                "latency_ms": latency, "error": str(exc), "checked_at": _now()}


def check_all(endpoints, *, timeout=10):
    return [check_endpoint(e["url"], timeout=timeout,
                           expected_status=e.get("expected_status", 200))
            for e in endpoints]


def summarise(results):
    up    = sum(1 for r in results if r["status"] == UP)
    down  = sum(1 for r in results if r["status"] == DOWN)
    latencies = [r["latency_ms"] for r in results if r["status"] == UP]
    avg_ms = round(sum(latencies) / len(latencies), 1) if latencies else None
    return {"total": len(results), "up": up, "down": down, "avg_latency_ms": avg_ms}


def save_report(report, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(report, indent=2))
    logger.info("Report written to %s", path)


def build_arg_parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", required=True, help='JSON file: [{"url": "...", "expected_status": 200}]')
    p.add_argument("--report", default="output/monitor_report.json")
    p.add_argument("--interval", type=int, default=0, help="Repeat every N seconds (0 = run once)")
    p.add_argument("--timeout", type=int, default=10)
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    endpoints = json.loads(Path(args.config).read_text())

    while True:
        results  = check_all(endpoints, timeout=args.timeout)
        summary  = summarise(results)
        report   = {"checked_at": _now(), "summary": summary, "results": results}
        save_report(report, args.report)
        logger.info("Summary: %d up / %d down  avg latency: %s ms",
                    summary["up"], summary["down"], summary["avg_latency_ms"])
        if args.interval == 0:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
