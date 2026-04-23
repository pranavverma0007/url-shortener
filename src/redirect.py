"""
GET /{code} — Lambda handler.

Looks up the short code in DynamoDB and returns a 302 redirect
to the original URL. Returns 404 if the code doesn't exist.
"""

import json

from src.db import get_url


def handler(event, context):
    """
    Lambda entry point for GET /{code}.

    Expected event (API Gateway HTTP API v2 format):
    {
        "pathParameters": { "code": "abc123" }
    }
    """
    # --- Extract short code from path ---
    path_params = event.get("pathParameters") or {}
    code = path_params.get("code")

    if not code:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing short code in URL path"}),
        }

    # --- Look up in DynamoDB ---
    long_url = get_url(code)

    if not long_url:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": f"Short code '{code}' not found"}),
        }

    # --- 302 Redirect ---
    return {
        "statusCode": 302,
        "headers": {
            "Location": long_url,
        },
        "body": "",
    }
