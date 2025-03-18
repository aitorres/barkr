"""
Module to implement unit tests for the RSS connection class
"""

from dataclasses import dataclass
from time import struct_time

import pytest

from barkr.connections import ConnectionMode, RSSConnection
from barkr.connections.rss import default_feed_message_callback
from barkr.models import Message


@dataclass(frozen=True)
class MockFeedParserFeedEntry:
    """
    Mock class for the feedparser feed entry
    """

    title: str
    link: str
    published_parsed: struct_time = struct_time((2025, 2, 27, 1, 0, 0, 1, 0, 0))


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

    # Reading skips messages that are older than the min_date
    monkeypatch.setattr(
        "feedparser.parse",
        lambda _: MockFeedParserFeed(
            entries=[
                MockFeedParserFeedEntry(
                    "New Title",
                    "https://new.example.com",
                    struct_time((2025, 3, 1, 1, 0, 1, 0, 0, 0)),
                ),
                MockFeedParserFeedEntry(
                    "Title",
                    "https://example.com",
                    struct_time((2025, 2, 27, 1, 0, 1, 0, 0, 0)),
                ),
            ]
        ),
    )
    rss.feed_min_date = struct_time((2025, 2, 28, 1, 0, 1, 0, 0, 0))
    messages = rss.read()
    assert len(messages) == 1
    assert messages[0].id == "https://new.example.com"
    assert messages[0].message == "New Title: https://new.example.com"

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
    rss.feed_min_date = None
    messages = rss.read()
    assert len(messages) == 1
    assert messages[0].id == "https://example.com"
    assert messages[0].message == "Custom: Title (https://example.com)"
    assert messages[0].message != "Title: https://example.com"
    assert messages[0].message == custom_callback("https://example.com", "Title")


def test_rssconnection_handles_exception_on_initial_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Test that the RSSConnection handles exceptions on initial fetch
    """

    # Mocking the feedparser.parse method to raise an exception
    monkeypatch.setattr(
        "feedparser.parse",
        lambda _: 1 / 0,
    )

    rss = RSSConnection(
        "RSSClass",
        [ConnectionMode.READ],
        "https://example.com",
    )
    assert rss.feed_min_date is None
    assert rss.feed_url == "https://example.com"

    # Simulating a successful fetch after the initial exception
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
    assert rss.feed_min_date is not None
