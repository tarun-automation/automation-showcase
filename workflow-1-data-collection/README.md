# Workflow 1: Data Collection

Collects records from a public JSON REST API and saves them locally as JSON or CSV.

## What it does

- Fetches data from a REST API endpoint (defaults to [jsonplaceholder.typicode.com/posts](https://jsonplaceholder.typicode.com/posts))
- Retries transient network/HTTP failures with exponential backoff
- Saves the collected records to `output/data.json` or `output/data.csv`

## Usage

From the repo root, with dependencies installed (`pip install -r requirements.txt`):

```bash
python workflow-1-data-collection/collector.py --url https://jsonplaceholder.typicode.com/posts --format json
```

Options:

| Flag | Description | Default |
|---|---|---|
| `--url` | API endpoint to collect data from | `https://jsonplaceholder.typicode.com/posts` |
| `--output-dir` | Directory to write output to | `output` |
| `--format` | `json` or `csv` | `json` |
| `--limit` | Max number of records to keep | none |
| `-v`, `--verbose` | Verbose logging | off |

## Tests

```bash
pytest workflow-1-data-collection/tests
```
