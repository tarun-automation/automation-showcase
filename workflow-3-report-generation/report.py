"""Generates a Markdown summary report from processed JSON/CSV records.

Designed to consume the output of workflow-2-file-processing, but works on
any JSON list-of-objects file or CSV file with a header row.
"""

import argparse
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def read_records(input_path):
    input_path = Path(input_path)
    if input_path.suffix.lower() == ".csv":
        with input_path.open(newline="") as f:
            return list(csv.DictReader(f))
    with input_path.open() as f:
        return json.load(f)


def _word_count(record):
    if "word_count" in record:
        return int(record["word_count"])
    body = record.get("body", "")
    return len(body.split()) if isinstance(body, str) else 0


def compute_summary(records, top_n=5):
    counts = [_word_count(r) for r in records]
    total = len(records)
    summary = {
        "total_records": total,
        "average_word_count": round(sum(counts) / total, 2) if total else 0,
        "min_word_count": min(counts) if counts else 0,
        "max_word_count": max(counts) if counts else 0,
    }
    ranked = sorted(records, key=_word_count, reverse=True)
    summary["top_records"] = [
        {
            "id": r.get("id"),
            "title": r.get("title"),
            "word_count": _word_count(r),
        }
        for r in ranked[:top_n]
    ]
    return summary


def render_markdown_report(summary, generated_at=None):
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    lines = [
        "# Data Processing Report",
        "",
        f"Generated: {generated_at}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Total records | {summary['total_records']} |",
        f"| Average word count | {summary['average_word_count']} |",
        f"| Min word count | {summary['min_word_count']} |",
        f"| Max word count | {summary['max_word_count']} |",
        "",
    ]

    if summary["top_records"]:
        lines += ["## Top Records by Word Count", "", "| ID | Title | Word Count |", "|---|---|---|"]
        for record in summary["top_records"]:
            lines.append(f"| {record['id']} | {record['title']} | {record['word_count']} |")
        lines.append("")
    else:
        lines += ["## Top Records by Word Count", "", "No records to display.", ""]

    return "\n".join(lines)


def write_report(content, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    logger.info("Wrote report to %s", output_path)


def build_arg_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to the input JSON or CSV file")
    parser.add_argument("--output", default="report.md", help="Path to write the Markdown report to")
    parser.add_argument("--top-n", type=int, default=5, help="Number of top records to include in the report")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    records = read_records(args.input)
    summary = compute_summary(records, top_n=args.top_n)
    report = render_markdown_report(summary)
    write_report(report, args.output)


if __name__ == "__main__":
    main()
