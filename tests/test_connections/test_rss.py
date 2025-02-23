"""
Module to implement unit tests for the RSS connection class
"""

from dataclasses import dataclass

import pytest

from barkr.connections import ConnectionMode, RSSConnection
from barkr.connections.rss import default_feed_message_callback
from barkr.models.message import Message


@dataclass(frozen=True)
class MockFeedParserFeedEntry:
    """
    Mock class for the feedparser feed entry
    """

    title: str
    link: str


@dataclass(frozen=True)
class MockFeedParserFeed:
    """
    Mock class for the feedparser feed
    """

    entries: list[MockFeedParserFeedEntry]


def test_rss_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Basic unit tests for the RSSConnection class
    """

    with pytest.raises(
        NotImplementedError, match="RSSConnection only supports read mode."
    ):
        RSSConnection(
            "RSSClass",
            [ConnectionMode.READ, ConnectionMode.WRITE],
            "https://example.com",
        )

    with pytest.raises(
        NotImplementedError, match="RSSConnection only supports read mode."
    ):
        RSSConnection(
            "RSSClass",
            [ConnectionMode.WRITE],
            "https://example.com",
        )

    rss = RSSConnection(
        "RSSClass",
        [ConnectionMode.READ],
        "https://example.com",
    )
    assert rss.name == "RSSClass"
    assert rss.feed_url == "https://example.com"
    assert rss.feed_message_callback is default_feed_message_callback
    assert rss.modes == [ConnectionMode.READ]

    # No writing at all!
    assert not rss.posted_message_ids
    rss.write([])
    rss.write([Message("id1", "test content")])
    rss.write([Message("id1", "test content"), Message("id2", "test content")])
    assert not rss.posted_message_ids

    # Reading returns a list of messages as expected
    monkeypatch.setattr(
        "feedparser.parse",
        lambda _: MockFeedParserFeed(
            entries=[MockFeedParserFeedEntry("Title", "https://example.com")]
        ),
    )
    messages = rss.read()
    assert len(messages) == 1
    assert messages[0].id == "https://example.com"
    assert messages[0].message == "Title: https://example.com"

    # Reading returns an empty list if the feed is empty
    monkeypatch.setattr(
        "feedparser.parse",
        lambda _: MockFeedParserFeed(entries=[]),
    )
    messages = rss.read()
    assert not messages

    # Reading returns an empty list if the feed throws an error
    monkeypatch.setattr(
        "feedparser.parse",
        lambda _: 1 / 0,
    )
    messages = rss.read()
    assert not messages

    # Reading returns a list of messages as expected with a custom callback
    def custom_callback(link: str, title: str) -> str:
        return f"Custom: {title} ({link})"

    rss = RSSConnection(
        "RSSClass",
        [ConnectionMode.READ],
        "https://example.com",
        custom_callback,
    )
    assert rss.feed_message_callback is custom_callback

    monkeypatch.setattr(
        "feedparser.parse",
        lambda _: MockFeedParserFeed(
            entries=[MockFeedParserFeedEntry("Title", "https://example.com")]
        ),
    )
    messages = rss.read()
    assert len(messages) == 1
    assert messages[0].id == "https://example.com"
    assert messages[0].message == "Custom: Title (https://example.com)"
    assert messages[0].message != "Title: https://example.com"
    assert messages[0].message == custom_callback("https://example.com", "Title")
