"""
Module to implement unit tests for the Bluesky connection class
"""

from dataclasses import dataclass
from typing import Optional

import pytest

from barkr.connections import BlueskyConnection, ConnectionMode


@dataclass(frozen=True)
class MockExternal:
    """
    Mock class to simulate a Bluesky external embed
    """

    title: str
    uri: str
    description: str


@dataclass(frozen=True)
class MockEmbed:
    """
    Mock class to simulate a Bluesky embed
    """

    external: Optional[MockExternal] = None
    py_type: str = "app.bsky.embed.external"


@dataclass(frozen=True)
class MockRecord:
    """
    Mock class to simulate a Bluesky record
    """

    text: str
    reply: Optional[str] = None
    embed: Optional[MockEmbed] = None


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


def test_bluesky_reconstructs_external_embeds_successfully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Test that the Bluesky connection reconstructs external embeds successfully.
    The test case reproduces a real-world scenario where, when a user posts a message
    that only contains a link, Bluesky can trim the actual URL in the post's message
    and include the full URL in the external embed.

    Since we're ignoring the embed in the generic Message, we need to reconstruct
    the URL on the message's text.
    """

    monkeypatch.setattr(
        "barkr.connections.bluesky.Client.login",
        lambda *_: None,
    )

    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_: MockFeed([]),
    )

    bsky = BlueskyConnection(
        "BlueskyClass",
        [ConnectionMode.READ],
        "test_handle",
        "test_password",
    )
    assert bsky.name == "BlueskyClass"

    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_args, **_kwargs: MockFeed(
            [
                MockPost(
                    MockPostData(
                        "2000-10-31T01:30:00.000-05:00",
                        MockRecord(
                            "open.spotify.com/track/0ElVpg...",
                            embed=MockEmbed(
                                external=MockExternal(
                                    title="Zombieboy",
                                    uri=(
                                        "https://open.spotify.com/track/0ElVp"
                                        "g9XIswx3XWs6kUj6a?si=0015d86587524ef9"
                                    ),
                                    description="Lady Gaga · MAYHEM · Song · 2025",
                                )
                            ),
                        ),
                    )
                ),
            ]
        ),
    )
    messages = bsky.read()
    assert len(messages) == 1
    assert messages[0].message == (
        "https://open.spotify.com/track/0ElVpg9XIswx3XWs6kUj6a?si=0015d86587524ef9"
    )

    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_args, **_kwargs: MockFeed(
            [
                MockPost(
                    MockPostData(
                        "2001-10-31T01:30:00.000-05:00",
                        MockRecord(
                            (
                                "GFOTY is always refreshing, "
                                "in a way open.spotify.com/track/3R9Pjd..."
                            ),
                            embed=MockEmbed(
                                external=MockExternal(
                                    title="spin song",
                                    uri=(
                                        "https://open.spotify.com/track/"
                                        "3R9PjdxlGKwGzo7ai89L8r?si=b7480cdf279e4fd8"
                                    ),
                                    description="GFOTY · INFLUENZER · Song · 2025",
                                )
                            ),
                        ),
                    )
                ),
            ]
        ),
    )
    messages = bsky.read()
    assert len(messages) == 1
    assert messages[0].message == (
        "GFOTY is always refreshing, in a way "
        "https://open.spotify.com/track/3R9PjdxlGKwGzo7ai89L8r?si=b7480cdf279e4fd8"
    )
