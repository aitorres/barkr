"""
Module to implement unit tests for the Twitter connection class
"""

from dataclasses import dataclass, field

import pytest

from barkr.connections import ConnectionMode, TwitterConnection
from barkr.models import Message


@dataclass(frozen=True)
class MockTweepyStatus:
    """
    Mock class for the Tweepy Status
    """

    id: int
    text: str


@dataclass(frozen=True)
class MockTweepyClient:
    """
    Mock class for the Tweepy Client
    """

    posted_statuses: list[str] = field(default_factory=list)

    def create_tweet(self, text: str) -> MockTweepyStatus:
        """
        Mock method for updating the status
        """

        self.posted_statuses.append(text)
        return MockTweepyStatus(len(self.posted_statuses), text)


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
            Message(id="1", message="test message 1"),
            Message(id="2", message="test message 2"),
        ]
    )

    assert twitter.posted_message_ids == {1, 2}
    assert mock_client.posted_statuses == ["test message 1", "test message 2"]

    # If a message is too long, it should be skipped
    twitter.write(
        [
            Message(id="3", message="a" * 300),
            Message(id="4", message="test message 4"),
        ]
    )
    assert mock_client.posted_statuses == [
        "test message 1",
        "test message 2",
        "test message 4",
    ]
