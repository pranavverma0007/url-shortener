# 🔗 Serverless URL Shortener

A lightweight, serverless URL shortener built with **AWS Lambda**, **API Gateway**, and **DynamoDB**, deployed using **AWS SAM** and automated with **GitHub Actions**.

## Architecture

```
Client ──► API Gateway (HTTP API v2)
               │
               ├── POST /shorten ──► ShortenFunction (Lambda)
               │                         │
               │                         ▼
               │                    DynamoDB (put_item)
               │
               └── GET /{code} ──► RedirectFunction (Lambda)
                                       │
                                       ▼
                                  DynamoDB (get_item)
                                       │
                                       ▼
                                  302 Redirect
```

## Project Structure

```
url-shortener/
├── src/
│   ├── __init__.py
│   ├── shorten.py          # POST /shorten Lambda handler
│   ├── redirect.py         # GET /{code} Lambda handler
│   └── db.py               # DynamoDB operations (shared)
├── tests/
│   ├── __init__.py
│   ├── test_shorten.py
│   └── test_redirect.py
├── template.yaml            # SAM template (IaC)
├── .github/workflows/
│   └── deploy.yml           # CI/CD pipeline
├── requirements.txt         # Runtime dependencies
├── requirements-dev.txt     # Dev/test dependencies
└── README.md
```

## Prerequisites

- Python 3.12+
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- AWS account with free-tier access
- (Optional) Docker — for `sam local invoke`

## Local Setup

```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate      # Linux/Mac
.\venv\Scripts\activate       # Windows

# 2. Install dev dependencies
pip install -r requirements-dev.txt

# 3. Run tests
pytest tests/ -v
```

## API Usage

### Shorten a URL

```bash
curl -X POST https://<api-id>.execute-api.<region>.amazonaws.com/prod/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/path"}'
```

**Response (201):**
```json
{
  "short_code": "abc123",
  "short_url": "https://<api-id>.execute-api.<region>.amazonaws.com/prod/abc123",
  "original_url": "https://example.com/very/long/path"
}
```

### Redirect

```bash
curl -L https://<api-id>.execute-api.<region>.amazonaws.com/prod/abc123
# → 302 Redirect to https://example.com/very/long/path
```

## Deployment

### Manual (SAM CLI)

```bash
sam build
sam deploy --guided    # First time — creates samconfig.toml
sam deploy             # Subsequent deployments
```

### Automated (GitHub Actions)

Add these secrets to your GitHub repo:

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Your IAM access key |
| `AWS_SECRET_ACCESS_KEY` | Your IAM secret key |
| `AWS_REGION` | e.g., `us-east-1` |
| `S3_BUCKET` | SAM deployment artifacts bucket |

Push to `main` → tests run → deploy to AWS automatically.

## Design Decisions

| Decision | Rationale |
|---|---|
| **PAY_PER_REQUEST** DynamoDB | No capacity planning, free-tier friendly (25 RCU/WCU free) |
| **HTTP API v2** (not REST API) | ~70% cheaper, lower latency, simpler |
| **302 (not 301)** redirect | Avoids browser caching — allows future link expiry/analytics |
| **`secrets.choice()`** for codes | Cryptographically secure randomness, not predictable `random.choice()` |
| **Conditional writes** in DynamoDB | Prevents short code collisions without a read-before-write |
| **Separated `db.py`** | All DB logic in one module — handlers stay thin and testable |

## Future Enhancements

- [ ] TTL-based link expiration
- [ ] Click analytics / hit counter
- [ ] Custom short codes (`POST /shorten` with `"code": "my-link"`)
- [ ] Rate limiting via API Gateway throttling
- [ ] Custom domain with Route 53 + ACM
