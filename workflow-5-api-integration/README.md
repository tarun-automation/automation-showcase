# Workflow 5: API Integration

REST API client with authentication, automatic retries, rate-limit handling, pagination, and full CRUD helpers.

## What it does

- Wraps `requests.Session` with a configurable base URL and shared connection pool
- Supports **API key**, **Bearer token**, and **HTTP Basic** authentication
- Retries transient network failures and 5xx errors with exponential backoff
- Respects `Retry-After` headers on 429 rate-limit responses
- Paginates collections automatically (RFC 5988 `Link` header or `page` query parameter)
- Exposes `get`, `post`, `put`, `patch`, and `delete` helpers with a CLI to exercise them

## Usage

From the repo root, with dependencies installed (`pip install -r requirements.txt`):

```bash
# Fetch a single resource
python workflow-5-api-integration/api_client.py get /posts/1

# List all records (paginated)
python workflow-5-api-integration/api_client.py list /posts --limit 10

# Create a resource
python workflow-5-api-integration/api_client.py create /posts --data '{"title":"Hello","body":"World","userId":1}'

# Replace a resource
python workflow-5-api-integration/api_client.py update /posts/1 --data '{"id":1,"title":"Updated","body":"Body","userId":1}'

# Delete a resource
python workflow-5-api-integration/api_client.py delete /posts/1
```

Use `--bearer-token` or `--api-key` for authenticated endpoints:

```bash
python workflow-5-api-integration/api_client.py --bearer-token mytoken get /me
```

### Options

| Flag | Description | Default |
|---|---|---|
| `--base-url` | API base URL | `https://jsonplaceholder.typicode.com` |
| `--bearer-token` | Bearer token for `Authorization` header | none |
| `--api-key` | API key sent as `X-Api-Key` header | none |
| `-v`, `--verbose` | Verbose logging | off |

## Using `APIClient` in your own code

```python
from api_client import APIClient

with APIClient("https://api.example.com", bearer_token="secret") as client:
    # Single resource
    post = client.get("/posts/1").json()

    # Create
    new_post = client.post("/posts", {"title": "Hi", "body": "There", "userId": 1}).json()

    # Paginate an entire collection
    for record in client.paginate("/posts", page_size=20):
        print(record["title"])
```

## Tests

```bash
pytest workflow-5-api-integration/tests
```
