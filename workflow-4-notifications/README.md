# Workflow 4: Notifications

Sends a notification built from a text file (e.g. a generated report) to
console, a local log file, or a webhook (Slack-compatible incoming webhook
format).

Designed to consume the output of [workflow-3-report-generation](../workflow-3-report-generation/),
but works on any plain-text input file.

## What it does

- Reads a text file and truncates it to a maximum notification length
- Sends the resulting message via one of three channels:
  - `console` — prints to stdout
  - `file` — appends a timestamped entry to a local log file
  - `webhook` — POSTs `{"text": message}` to a webhook URL, retrying transient failures with backoff

## Usage

From the repo root, with dependencies installed (`pip install -r requirements.txt`):

```bash
python workflow-4-notifications/notifier.py --input workflow-3-report-generation/report.md --channel console
```

Send to a log file instead:

```bash
python workflow-4-notifications/notifier.py --input workflow-3-report-generation/report.md --channel file --output notifications.log
```

Send to a webhook:

```bash
python workflow-4-notifications/notifier.py --input workflow-3-report-generation/report.md --channel webhook --webhook-url https://hooks.example.com/services/...
```

Options:

| Flag | Description | Default |
|---|---|---|
| `--input` | Path to the text file to notify about | required |
| `--channel` | `console`, `file`, or `webhook` | `console` |
| `--output` | Log file path when `--channel=file` | `notifications.log` |
| `--webhook-url` | Webhook URL when `--channel=webhook` | none |
| `--max-length` | Maximum notification message length | `500` |
| `-v`, `--verbose` | Verbose logging | off |

## Tests

```bash
pytest workflow-4-notifications/tests
```
