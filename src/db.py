"""
DynamoDB operations for the URL shortener.

This module is the ONLY place that talks to DynamoDB.
Adding features like TTL, click counts, or metadata
means extending this module — handlers stay untouched.
"""

import os
import boto3
from botocore.exceptions import ClientError

# Table name injected via environment variable (set in template.yaml)
TABLE_NAME = os.environ.get("TABLE_NAME", "url-shortener-table")

# Reuse the client across warm Lambda invocations (connection pooling)
_dynamodb = None


def _get_table():
    """Lazy-initialize the DynamoDB Table resource."""
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb").Table(TABLE_NAME)
    return _dynamodb


def put_url(short_code: str, long_url: str) -> bool:
    """
    Store a short_code → long_url mapping in DynamoDB.

    Uses a ConditionExpression to prevent overwriting an existing code
    (handles the astronomically rare collision case).

    Returns True if stored successfully, False if the code already exists.
    """
    table = _get_table()
    try:
        table.put_item(
            Item={
                "short_code": short_code,
                "long_url": long_url,
            },
            ConditionExpression="attribute_not_exists(short_code)",
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise  # Re-raise unexpected errors


def get_url(short_code: str) -> str | None:
    """
    Look up the original URL for a given short code.

    Returns the long_url string, or None if not found.
    """
    table = _get_table()
    response = table.get_item(Key={"short_code": short_code})
    item = response.get("Item")
    return item["long_url"] if item else None
