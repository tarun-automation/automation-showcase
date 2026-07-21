# Workflow 3: Report Generation

Generates a Markdown summary report from processed JSON or CSV records.

Designed to consume the output of [workflow-2-file-processing](../workflow-2-file-processing/),
but works on any JSON list-of-objects file or CSV file with a header row.

## What it does

- Computes total record count, average/min/max word count
- Ranks records by word count and lists the top N in the report
- Renders a Markdown report with summary and top-records tables

## Usage

From the repo root, with dependencies installed (`pip install -r requirements.txt`):

```bash
python workflow-3-report-generation/report.py --input workflow-2-file-processing/output/processed.json --output report.md
```

Options:

| Flag | Description | Default |
|---|---|---|
| `--input` | Path to the input JSON or CSV file | required |
| `--output` | Path to write the Markdown report to | `report.md` |
| `--top-n` | Number of top records to include | `5` |
| `-v`, `--verbose` | Verbose logging | off |

## Tests

```bash
pytest workflow-3-report-generation/tests
```
