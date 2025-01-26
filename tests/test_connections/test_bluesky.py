"""
Module to implement unit tests for the Bluesky connection class
"""

from dataclasses import dataclass
from typing import Optional

import pytest

from barkr.connections.base import ConnectionMode
from barkr.connections.bluesky import BlueskyConnection


@dataclass(frozen=True)
class MockRecord:
    """
    Mock class to simulate a Bluesky record
    """

    text: str
    reply: Optional[str] = None


@dataclass(frozen=True)
class MockPostData:
    """
    Mock class to simulate a Bluesky post data
    """

    indexed_at: str
    record: MockRecord
    viewer: Optional[str] = None


@dataclass(frozen=True)
class MockPost:
    """
    Mock class to simulate a Bluesky post
    """

    post: MockPostData


@dataclass(frozen=True)
class MockFeed:
    """
    Mock class to simulate a Bluesky feed
    """

    feed: list[MockPost]


def test_bluesky_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Basic unit tests for the BlueskyConnection class
    """

    monkeypatch.setattr(
        "barkr.connections.bluesky.Client.login",
        lambda *_: None,
    )

    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_: MockFeed([]),
    )

    bluesky_no_initial_messages = BlueskyConnection(
        "BlueskyClass",
        [ConnectionMode.READ, ConnectionMode.WRITE],
        "test_handle",
        "test_password",
    )
    assert bluesky_no_initial_messages.name == "BlueskyClass"
    assert bluesky_no_initial_messages.min_id is None

    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_args, **_kwargs: MockFeed(
            [
                MockPost(
                    MockPostData(
                        "2000-10-31T01:30:00.000-05:00", MockRecord("Hello, world!")
                    )
                ),
                MockPost(
                    MockPostData(
                        "2000-10-29T01:30:00.000-05:00", MockRecord("Goodbye, world!")
                    )
                ),
            ]
        ),
    )

    bluesky = BlueskyConnection(
        "BlueskyClass",
        [ConnectionMode.READ, ConnectionMode.WRITE],
        "test_handle",
        "test_password",
    )

    assert bluesky.name == "BlueskyClass"
    assert bluesky.min_id == "2000-10-31T01:30:00.000-05:00"

    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_args, **_kwargs: MockFeed([]),
    )
    messages = bluesky.read()
    assert not messages

    # Reading one message
    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_args, **_kwargs: MockFeed(
            [
                MockPost(
                    MockPostData(
                        "2000-10-31T02:30:00.000-05:00", MockRecord("Hello, world 2!")
                    )
                ),
                MockPost(
                    MockPostData(
                        "2000-10-31T01:30:00.000-05:00", MockRecord("Goodbye, world!")
                    )
                ),
            ]
        ),
    )
    messages = bluesky.read()
    assert len(messages) == 1

    # Reading again, no new messages since we increased the min_id
    messages = bluesky.read()
    assert not messages

    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_args, **_kwargs: MockFeed(
            [
                MockPost(
                    MockPostData(
                        "2001-10-31T02:30:00.000-05:00",
                        MockRecord("Hello, world 2!", reply="12345678"),
                    )
                ),
            ]
        ),
    )
    messages = bluesky.read()
    assert len(messages) == 0
