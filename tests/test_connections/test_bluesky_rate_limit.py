"""Tests for Bluesky rate-limit diagnostics."""

import pytest
from atproto_client.exceptions import RateLimitExceededError
from atproto_client.request import Response

from barkr.connections import BlueskyConnection, ConnectionMode
from barkr.models import Message
from tests.mocks.bluesky import MockFeed


def _create_connection(monkeypatch: pytest.MonkeyPatch) -> BlueskyConnection:
    """Create a connection without making real Bluesky requests."""
    monkeypatch.setattr("barkr.connections.bluesky.Client.login", lambda *_: None)
    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_: MockFeed([]),
    )
    return BlueskyConnection(
        "BlueskyRateLimit",
        [ConnectionMode.READ, ConnectionMode.WRITE],
        "test_handle",
        "test_password",
    )


def _rate_limit_error(headers: dict[str, str]) -> RateLimitExceededError:
    return RateLimitExceededError(
        response=Response(
            success=False,
            status_code=429,
            content=None,
            headers=headers,
        )
    )


def test_feed_rate_limit_logs_headers_and_retry_delay(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Rate-limit logs include quota headers and scheduled retry delay."""
    connection = _create_connection(monkeypatch)
    sleep_delays: list[float] = []
    monkeypatch.setattr("time.sleep", sleep_delays.append)
    rate_limit_error = _rate_limit_error(
        {
            "ratelimit-limit": "100",
            "ratelimit-remaining": "0",
            "ratelimit-reset": "1893456000",
            "ratelimit-policy": "100;w=300",
            "retry-after": "5",
            "content-type": "application/json",
        }
    )
    feed_calls = 0

    def mock_get_author_feed(*_args, **_kwargs):
        nonlocal feed_calls
        feed_calls += 1
        if feed_calls == 1:
            raise rate_limit_error
        return MockFeed([])

    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        mock_get_author_feed,
    )

    # pylint: disable=protected-access
    with caplog.at_level("WARNING"):
        feed = connection._get_user_feed_with_retry()
        assert feed == []
    # pylint: enable=protected-access

    assert sleep_delays == [0.1]
    assert "limit=100 remaining=0" in caplog.text
    assert "policy=100;w=300" in caplog.text
    assert "retry_after_seconds=5.0" in caplog.text
    assert "retry_after_header=5" in caplog.text
    assert "scheduled_retry_delay=0.1" in caplog.text
    assert "content-type" not in caplog.text


def test_post_rate_limit_logs_metadata_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Posting rate limits are logged and remain visible to the caller."""
    connection = _create_connection(monkeypatch)
    rate_limit_error = _rate_limit_error(
        {"ratelimit-limit": "10", "ratelimit-remaining": "0"}
    )
    monkeypatch.setattr(
        "barkr.connections.bluesky.Client.send_post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(rate_limit_error),
    )

    with caplog.at_level("WARNING"), pytest.raises(RateLimitExceededError):
        connection._post(  # pylint: disable=protected-access
            [Message(id="src-1", message="msg", source_connection="test")]
        )

    assert "posting rate limited (HTTP 429)" in caplog.text
    assert "limit=10 remaining=0" in caplog.text
