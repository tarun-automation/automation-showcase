"""Cleans, validates, deduplicates, and enriches records from a JSON/CSV file.

Designed to consume the output produced by workflow-1-data-collection, but
works on any JSON list-of-objects file or CSV file with a header row.
"""

import argparse
import csv
import json
import logging
from pathlib import Path

DEFAULT_REQUIRED_FIELDS = ("id", "title", "body")

logger = logging.getLogger(__name__)


def read_records(input_path):
    input_path = Path(input_path)
    if input_path.suffix.lower() == ".csv":
        with input_path.open(newline="") as f:
            return list(csv.DictReader(f))
    with input_path.open() as f:
        return json.load(f)


def write_records(records, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".csv":
        if not records:
            output_path.write_text("")
            return
        with output_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)
        return
    with output_path.open("w") as f:
        json.dump(records, f, indent=2)


def clean_record(record):
    """Strip surrounding whitespace from every string field."""
    return {key: (value.strip() if isinstance(value, str) else value) for key, value in record.items()}


def is_valid(record, required_fields=DEFAULT_REQUIRED_FIELDS):
    """A record is valid if every required field is present and non-empty."""
    return all(record.get(field) not in (None, "") for field in required_fields)


def deduplicate(records, key="id"):
    """Keep the first occurrence of each value of `key`, preserving order."""
    seen = set()
    deduped = []
    for record in records:
        value = record.get(key)
        if value in seen:
            continue
        seen.add(value)
        deduped.append(record)
    return deduped


def enrich_with_word_count(record, field="body"):
    text = record.get(field)
    word_count = len(text.split()) if isinstance(text, str) else 0
    return {**record, "word_count": word_count}


def process_records(records, required_fields=DEFAULT_REQUIRED_FIELDS):
    cleaned = [clean_record(r) for r in records]
    valid = [r for r in cleaned if is_valid(r, required_fields)]
    deduped = deduplicate(valid)
    enriched = [enrich_with_word_count(r) for r in deduped]
    logger.info(
        "Processed %d input records -> %d valid, %d after dedup",
        len(records),
        len(valid),
        len(enriched),
    )
    return enriched


def build_arg_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to the input JSON or CSV file")
    parser.add_argument("--output", required=True, help="Path to write the processed JSON or CSV file")
    parser.add_argument(
        "--required-fields",
        default=",".join(DEFAULT_REQUIRED_FIELDS),
        help="Comma-separated list of fields a record must have to be kept",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    required_fields = tuple(f.strip() for f in args.required_fields.split(",") if f.strip())
    records = read_records(args.input)
    processed = process_records(records, required_fields)
    write_records(processed, args.output)


if __name__ == "__main__":
    main()
