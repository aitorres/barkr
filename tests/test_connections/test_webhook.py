"""
Module to implement unit tests for the Webhook connection class
"""

from typing import Any
from unittest.mock import MagicMock

import pytest
from requests.exceptions import RequestException

from barkr.connections import ConnectionMode, WebhookConnection
from barkr.models import Message


def test_webhook_connection() -> None:
    """
    Basic unit tests for the WebhookConnection class
    """

    with pytest.raises(
        NotImplementedError, match="WebhookConnection only supports write mode."
    ):
        WebhookConnection(
            "WebhookClass",
            [ConnectionMode.READ],
            "https://example.com/webhook",
        )

    with pytest.raises(
        NotImplementedError, match="WebhookConnection only supports write mode."
    ):
        WebhookConnection(
            "WebhookClass",
            [ConnectionMode.READ, ConnectionMode.WRITE],
            "https://example.com/webhook",
        )

    webhook = WebhookConnection(
        "Webhook Connection",
        [ConnectionMode.WRITE],
        "https://example.com/webhook",
    )
    assert webhook.name == "Webhook Connection"
    assert webhook.modes == [ConnectionMode.WRITE]
    assert webhook.webhook_endpoint == "https://example.com/webhook"
    assert webhook.payload_key == "content"
    assert webhook.auth_token is None
    assert webhook.posted_message_ids == set()

    # Reading never returns anything other than an empty list
    assert not webhook.read()


def test_webhook_connection_with_custom_params() -> None:
    """
    Test WebhookConnection with custom parameters
    """
    webhook = WebhookConnection(
        "Custom Webhook",
        [ConnectionMode.WRITE],
        webhook_endpoint="https://api.example.com/notify",
        payload_key="data",
        auth_token="my-secret-token",
    )

    assert webhook.webhook_endpoint == "https://api.example.com/notify"
    assert webhook.payload_key == "data"
    assert webhook.auth_token == "my-secret-token"


def test_webhook_connection_validation() -> None:
    """
    Test WebhookConnection parameter validation
    """

    with pytest.raises(ValueError, match="non-empty webhook endpoint"):
        WebhookConnection(
            "Invalid",
            [ConnectionMode.WRITE],
            webhook_endpoint="",
        )

    with pytest.raises(ValueError, match="non-empty webhook endpoint"):
        WebhookConnection(
            "Invalid",
            [ConnectionMode.WRITE],
            webhook_endpoint="   ",
        )

    with pytest.raises(ValueError, match="valid URL"):
        WebhookConnection(
            "Invalid",
            [ConnectionMode.WRITE],
            webhook_endpoint="not-a-url",
        )

    with pytest.raises(ValueError, match="valid URL"):
        WebhookConnection(
            "Invalid",
            [ConnectionMode.WRITE],
            webhook_endpoint="ftp://example.com",
        )


def test_webhook_connection_post(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test WebhookConnection._post() sends correct payload
    """

    webhook = WebhookConnection(
        "WriteWebhook",
        [ConnectionMode.WRITE],
        webhook_endpoint="https://example.com/webhook",
        payload_key="data",
    )

    captured_requests: list[dict[str, Any]] = []

    def mock_post(
        url: str, json: dict, headers: dict, *_args: Any, **_kwargs: Any
    ) -> MagicMock:
        captured_requests.append({"url": url, "json": json, "headers": headers})
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        return response

    monkeypatch.setattr("requests.post", mock_post)

    messages = [
        Message(id="1", message="Hello World", source_connection="test"),
        Message(id="2", message="Goodbye World", source_connection="test"),
    ]

    posted_ids = webhook._post(messages)  # pylint: disable=protected-access

    assert len(posted_ids) == 2
    assert len(captured_requests) == 2

    assert captured_requests[0]["url"] == "https://example.com/webhook"
    assert captured_requests[0]["json"] == {"data": "Hello World"}
    assert "Authorization" not in captured_requests[0]["headers"]

    assert captured_requests[1]["url"] == "https://example.com/webhook"
    assert captured_requests[1]["json"] == {"data": "Goodbye World"}


def test_webhook_connection_post_with_auth_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Test WebhookConnection._post() sends Authorization header when auth_token is set
    """
    webhook = WebhookConnection(
        "WriteWebhook",
        [ConnectionMode.WRITE],
        webhook_endpoint="https://example.com/webhook",
        auth_token="my-secret-token",
    )

    captured_headers: dict[str, str] = {}

    def mock_post(*_args: Any, **_kwargs: Any) -> MagicMock:
        headers = _kwargs.get("headers", {})
        captured_headers.update(headers)
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        return response

    monkeypatch.setattr("requests.post", mock_post)

    messages = [Message(id="1", message="Test", source_connection="test")]
    webhook._post(messages)  # pylint: disable=protected-access

    assert captured_headers["Authorization"] == "Bearer my-secret-token"


def test_webhook_connection_post_handles_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test WebhookConnection._post() handles request errors gracefully
    """

    webhook = WebhookConnection(
        "WriteWebhook",
        [ConnectionMode.WRITE],
        webhook_endpoint="https://example.com/webhook",
    )

    def mock_post(*_args: Any, **_kwargs: Any) -> None:
        raise RequestException("Connection failed")

    monkeypatch.setattr("requests.post", mock_post)

    messages = [Message(id="1", message="Test message", source_connection="test")]

    # Should not raise, but return empty list
    posted_ids = webhook._post(messages)  # pylint: disable=protected-access
    assert not posted_ids


def test_webhook_connection_write_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test the full write() flow through the base class
    """
    webhook = WebhookConnection(
        "WriteWebhook",
        [ConnectionMode.WRITE],
        webhook_endpoint="https://example.com/webhook",
    )

    call_count = 0

    def mock_post(*_args: Any, **_kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        return response

    monkeypatch.setattr("requests.post", mock_post)

    assert call_count == 0
    webhook.write([Message("test_id", "test message", source_connection="test")])
    assert call_count == 1

    webhook.write([Message("test_id2", "test message 2", source_connection="test")])
    assert call_count == 2
