"""
Module to implement unit tests for the Twitter connection class
"""

from dataclasses import dataclass, field
from typing import Any, Optional

import pytest

from barkr.connections import ConnectionMode, TwitterConnection
from barkr.models import Message


@dataclass(frozen=True)
class MockTweepyStatusResponse:
    """
    Mock class for the Tweepy Status
    """

    id: int
    text: str

    @property
    def data(self) -> dict[str, Any]:
        """
        Mock method for the data property
        """

        return {"id": self.id, "text": self.text}


@dataclass
class MockTweepyClient:
    """
    Mock class for the Tweepy Client
    """

    posted_statuses: list[tuple[str, Optional[str]]] = field(default_factory=list)

    def create_tweet(
        self, text: str, in_reply_to_tweet_id: Optional[str] = None
    ) -> MockTweepyStatusResponse:
        """
        Mock method for creating a tweet
        """

        self.posted_statuses.append((text, in_reply_to_tweet_id))
        return MockTweepyStatusResponse(len(self.posted_statuses), text)


def test_twitter_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Basic unit tests for the TwitterConnection class
    """

    with pytest.raises(
        NotImplementedError, match="TwitterConnection only supports write mode."
    ):
        TwitterConnection(
            "TwitterClass",
            [ConnectionMode.READ],
            "test_consumer_key",
            "test_consumer_secret",
            "test_access_token",
            "test_access_token_secret",
            "test_bearer_token",
        )

    with pytest.raises(
        NotImplementedError, match="TwitterConnection only supports write mode."
    ):
        TwitterConnection(
            "TwitterClass",
            [ConnectionMode.READ, ConnectionMode.WRITE],
            "test_consumer_key",
            "test_consumer_secret",
            "test_access_token",
            "test_access_token_secret",
            "test_bearer_token",
        )

    mock_client = MockTweepyClient()
    monkeypatch.setattr(
        "barkr.connections.twitter.Client",
        lambda *args, **kwargs: mock_client,
    )

    twitter = TwitterConnection(
        "Twitter Connection",
        [ConnectionMode.WRITE],
        "test_consumer_key",
        "test_consumer_secret",
        "test_access_token",
        "test_access_token_secret",
        "test_bearer_token",
    )
    assert twitter.name == "Twitter Connection"

    # Reading never returns anything other than an empty list
    assert not twitter.read()

    assert twitter.posted_message_ids == set()

    twitter.write(
        [
            Message(id="1", message="test message 1", source_connection="test"),
            Message(id="2", message="test message 2", source_connection="test"),
        ]
    )

    assert twitter.posted_message_ids == {1, 2}
    assert mock_client.posted_statuses == [
        ("test message 1", None),
        ("test message 2", None),
    ]

    # If a message is too long, it should be skipped
    twitter.write(
        [
            Message(id="3", message="a" * 300, source_connection="test"),
            Message(id="4", message="test message 4", source_connection="test"),
        ]
    )
    assert mock_client.posted_statuses == [
        ("test message 1", None),
        ("test message 2", None),
        ("test message 4", None),
    ]


def test_twitter_thread_support(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Unit tests for Twitter threading/reply support
    """

    mock_client = MockTweepyClient()
    monkeypatch.setattr(
        "barkr.connections.twitter.Client",
        lambda *args, **kwargs: mock_client,
    )

    twitter = TwitterConnection(
        "Twitter Connection",
        [ConnectionMode.WRITE],
        "test_consumer_key",
        "test_consumer_secret",
        "test_access_token",
        "test_access_token_secret",
        "test_bearer_token",
    )

    twitter.write(
        [
            Message(id="source_1", message="Thread start", source_connection="source"),
        ]
    )

    assert len(mock_client.posted_statuses) == 1
    assert mock_client.posted_statuses[0] == ("Thread start", None)

    assert ("source", "source_1") in twitter.message_id_map
    assert twitter.message_id_map[("source", "source_1")]["Twitter Connection"] == 1

    twitter.write(
        [
            Message(
                id="source_2",
                message="Thread reply",
                source_connection="source",
                reply_to_id="source_1",
            ),
        ]
    )

    assert len(mock_client.posted_statuses) == 2
    assert mock_client.posted_statuses[1] == ("Thread reply", 1)

    assert ("source", "source_2") in twitter.message_id_map
    assert twitter.message_id_map[("source", "source_2")]["Twitter Connection"] == 2

    twitter.write(
        [
            Message(
                id="source_3",
                message="Orphan reply",
                source_connection="source",
                reply_to_id="non_existent_parent",
            ),
        ]
    )

    assert len(mock_client.posted_statuses) == 2


def test_twitter_multiple_connections_thread_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Unit tests to verify that each connection maintains its own mapping
    for the same source message ID
    """

    mock_client_1 = MockTweepyClient()
    mock_client_2 = MockTweepyClient()

    create_mock_client_called = 0

    def create_mock_client(*_args: Any, **_kwargs: Any) -> MockTweepyClient:
        nonlocal create_mock_client_called
        create_mock_client_called += 1
        return mock_client_1 if create_mock_client_called == 1 else mock_client_2

    monkeypatch.setattr(
        "barkr.connections.twitter.Client",
        create_mock_client,
    )

    twitter_1 = TwitterConnection(
        "Twitter Connection 1",
        [ConnectionMode.WRITE],
        "test_consumer_key",
        "test_consumer_secret",
        "test_access_token",
        "test_access_token_secret",
        "test_bearer_token",
    )

    twitter_2 = TwitterConnection(
        "Twitter Connection 2",
        [ConnectionMode.WRITE],
        "test_consumer_key",
        "test_consumer_secret",
        "test_access_token",
        "test_access_token_secret",
        "test_bearer_token",
    )

    message = Message(
        id="source_1", message="Cross-posted message", source_connection="source"
    )
    twitter_1.write([message])
    twitter_2.write([message])

    assert len(mock_client_1.posted_statuses) == 1
    assert len(mock_client_2.posted_statuses) == 1

    key = ("source", "source_1")
    assert key in TwitterConnection.message_id_map
    assert TwitterConnection.message_id_map[key]["Twitter Connection 1"] == 1
    assert TwitterConnection.message_id_map[key]["Twitter Connection 2"] == 1

    reply_message = Message(
        id="source_2",
        message="Reply message",
        source_connection="source",
        reply_to_id="source_1",
    )
    twitter_1.write([reply_message])
    twitter_2.write([reply_message])

    assert mock_client_1.posted_statuses[1] == ("Reply message", 1)
    assert mock_client_2.posted_statuses[1] == ("Reply message", 1)
