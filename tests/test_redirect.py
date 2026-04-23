"""Tests for GET /{code} redirect handler."""

import json
import os
import boto3
import pytest
from moto import mock_aws

os.environ["TABLE_NAME"] = "test-url-table"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"

import src.db as db_module


@pytest.fixture(autouse=True)
def dynamodb_table():
    """Create a mock DynamoDB table with a pre-seeded URL mapping."""
    with mock_aws():
        # Reset the cached DynamoDB resource so it initializes inside the mock
        db_module._dynamodb = None

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

        # Seed a known mapping for redirect tests
        table.put_item(
            Item={
                "short_code": "abc123",
                "long_url": "https://example.com/original",
            }
        )

        yield table

        db_module._dynamodb = None


@pytest.fixture
def redirect_event():
    """Factory for redirect API Gateway events."""
    def _make_event(code: str | None = None):
        event = {}
        if code is not None:
            event["pathParameters"] = {"code": code}
        else:
            event["pathParameters"] = None
        return event
    return _make_event


class TestRedirectHandler:
    """Test suite for the redirect Lambda handler."""

    def test_redirect_existing_code(self, redirect_event):
        """Should return 302 with Location header for a known short code."""
        from src.redirect import handler

        response = handler(redirect_event("abc123"), None)

        assert response["statusCode"] == 302
        assert response["headers"]["Location"] == "https://example.com/original"

    def test_redirect_unknown_code(self, redirect_event):
        """Should return 404 for a short code that doesn't exist."""
        from src.redirect import handler

        response = handler(redirect_event("zzz999"), None)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert "not found" in body["error"]

    def test_redirect_missing_path_param(self, redirect_event):
        """Should return 400 when no code is in the path."""
        from src.redirect import handler

        response = handler(redirect_event(None), None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Missing" in body["error"]
