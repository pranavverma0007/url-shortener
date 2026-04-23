"""Tests for POST /shorten handler."""

import json
import os
import boto3
import pytest
from moto import mock_aws

# Set env BEFORE importing handler (handler reads TABLE_NAME at import time)
os.environ["TABLE_NAME"] = "test-url-table"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"

import src.db as db_module


@pytest.fixture(autouse=True)
def dynamodb_table():
    """Create a mock DynamoDB table for testing."""
    with mock_aws():
        # Reset the cached DynamoDB resource so it initializes inside the mock
        db_module._dynamodb = None

        # Create the mock table
        client = boto3.resource("dynamodb", region_name="us-east-1")
        table = client.create_table(
            TableName="test-url-table",
            KeySchema=[{"AttributeName": "short_code", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "short_code", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.meta.client.get_waiter("table_exists").wait(
            TableName="test-url-table"
        )

        yield table

        # Clean up cached resource after each test
        db_module._dynamodb = None


@pytest.fixture
def api_event():
    """Factory for API Gateway HTTP API v2 events."""
    def _make_event(body: dict | None = None):
        return {
            "body": json.dumps(body) if body else None,
            "requestContext": {
                "domainName": "abc123.execute-api.us-east-1.amazonaws.com",
            },
        }
    return _make_event


class TestShortenHandler:
    """Test suite for the shorten Lambda handler."""

    def test_shorten_valid_url(self, api_event):
        """Should return 201 with a short code for a valid URL."""
        from src.shorten import handler

        event = api_event({"url": "https://example.com/long/path"})
        response = handler(event, None)

        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert "short_code" in body
        assert len(body["short_code"]) == 6
        assert body["original_url"] == "https://example.com/long/path"
        assert body["short_code"] in body["short_url"]

    def test_shorten_missing_url(self, api_event):
        """Should return 400 when 'url' field is missing."""
        from src.shorten import handler

        event = api_event({"not_url": "something"})
        response = handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Missing" in body["error"]

    def test_shorten_invalid_url(self, api_event):
        """Should return 400 for URLs without http/https scheme."""
        from src.shorten import handler

        event = api_event({"url": "ftp://not-a-web-url.com"})
        response = handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Invalid URL" in body["error"]

    def test_shorten_invalid_json(self):
        """Should return 400 when body is not valid JSON."""
        from src.shorten import handler

        event = {"body": "this is not json"}
        response = handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Invalid JSON" in body["error"]

    def test_shorten_empty_body(self):
        """Should return 400 when body is empty/None."""
        from src.shorten import handler

        event = {"body": None}
        response = handler(event, None)

        assert response["statusCode"] == 400

    def test_shorten_stores_in_dynamodb(self, dynamodb_table, api_event):
        """Should actually store the URL mapping in DynamoDB."""
        from src.shorten import handler

        event = api_event({"url": "https://example.com"})
        response = handler(event, None)
        body = json.loads(response["body"])

        # Verify it was stored
        result = dynamodb_table.get_item(
            Key={"short_code": body["short_code"]}
        )
        assert result["Item"]["long_url"] == "https://example.com"
