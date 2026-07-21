# Workflow 2: File Processing

Cleans, validates, deduplicates, and enriches records from a JSON or CSV file.

Designed to consume the output of [workflow-1-data-collection](../workflow-1-data-collection/),
but works on any JSON list-of-objects file or CSV file with a header row.

## What it does

- Strips surrounding whitespace from string fields
- Drops records missing any required field (default: `id`, `title`, `body`)
- Deduplicates records by `id`, keeping the first occurrence
- Adds a `word_count` field derived from the `body` field
- Reads and writes both JSON and CSV, based on file extension

## Usage

From the repo root, with dependencies installed (`pip install -r requirements.txt`):

```bash
python workflow-2-file-processing/processor.py --input workflow-1-data-collection/output/data.json --output output/processed.json
```

Options:

| Flag | Description | Default |
|---|---|---|
| `--input` | Path to the input JSON or CSV file | required |
| `--output` | Path to write the processed JSON or CSV file | required |
| `--required-fields` | Comma-separated fields a record must have to be kept | `id,title,body` |
| `-v`, `--verbose` | Verbose logging | off |

## Tests

```bash
pytest workflow-2-file-processing/tests
```
