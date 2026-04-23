"""
POST /shorten — Lambda handler.

Accepts a JSON body with a "url" field, generates a 6-character short code,
stores the mapping, and returns the short URL.
"""

import json
import string
import secrets

from src.db import put_url

# Character set: a-z, A-Z, 0-9 → 62 chars → 62^6 ≈ 56 billion combinations
CHARSET = string.ascii_letters + string.digits
CODE_LENGTH = 6
# Max retries in case of collision (extremely unlikely)
MAX_RETRIES = 3


def _generate_code(length: int = CODE_LENGTH) -> str:
    """Generate a cryptographically random short code."""
    return "".join(secrets.choice(CHARSET) for _ in range(length))


def _is_valid_url(url: str) -> bool:
    """Basic URL validation — must start with http:// or https://."""
    return isinstance(url, str) and url.startswith(("http://", "https://"))


def handler(event, context):
    """
    Lambda entry point for POST /shorten.

    Expected event (API Gateway HTTP API v2 format):
    {
        "body": "{\"url\": \"https://example.com/long/path\"}"
    }
    """
    # --- Parse request body ---
    try:
        body = json.loads(event.get("body", "{}"))
    except (json.JSONDecodeError, TypeError):
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON body"}),
        }

    long_url = body.get("url")

    # --- Validate input ---
    if not long_url:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing 'url' field"}),
        }

    if not _is_valid_url(long_url):
        return {
            "statusCode": 400,
            "body": json.dumps(
                {"error": "Invalid URL. Must start with http:// or https://"}
            ),
        }

    # --- Generate short code and store ---
    for _ in range(MAX_RETRIES):
        code = _generate_code()
        if put_url(code, long_url):
            return {
                "statusCode": 201,
                "body": json.dumps(
                    {
                        "short_code": code,
                        "short_url": f"https://{event.get('requestContext', {}).get('domainName', 'localhost')}/{code}",
                        "original_url": long_url,
                    }
                ),
            }

    # All retries exhausted (virtually impossible)
    return {
        "statusCode": 500,
        "body": json.dumps({"error": "Failed to generate unique code. Try again."}),
    }
