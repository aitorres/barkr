"""
Module to implement unit tests for the Bluesky connection class
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pytest
from atproto_client.models import AppBskyEmbedExternal  # type: ignore
from atproto_client.models.blob_ref import BlobRef  # type: ignore
from bs4 import BeautifulSoup

from barkr.connections import BlueskyConnection, ConnectionMode
from barkr.connections.bluesky import (
    _get_current_indexed_at,
    _get_meta_tag_from_html_metadata,
)


@dataclass(frozen=True)
class MockResponse:
    """
    Mock class to simulate the response of requests.get
    """

    content: bytes
    status_code: int


@dataclass(frozen=True)
class MockExternal:
    """
    Mock class to simulate a Bluesky external embed
    """

    title: str
    uri: str
    description: str


@dataclass(frozen=True)
class MockExternalEmbed:
    """
    Mock class to simulate a Bluesky external embed
    """

    external: Optional[MockExternal] = None


@dataclass(frozen=True)
class MockRecord:
    """
    Mock class to simulate a Bluesky record
    """

    text: str
    reply: Optional[str] = None
    embed: Optional[MockExternalEmbed] = None
    langs: Optional[list[str]] = None


@dataclass(frozen=True)
class MockViewer:
    """
    Mock class to simulate the viewer of a Bluesky post
    """

    # NOTE: this is not a string in the real contract, but enough
    # for our tests
    repost: Optional[str] = None


@dataclass(frozen=True)
class MockPostData:
    """
    Mock class to simulate a Bluesky post data
    """

    indexed_at: str
    record: MockRecord
    viewer: Optional[MockViewer] = None


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
    assert messages[0].message == "Hello, world 2!"
    assert messages[0].language is None

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

    # Testing that Bluesky ignores posts that are reposts
    bluesky.min_id = None
    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_args, **_kwargs: MockFeed(
            [
                MockPost(
                    MockPostData(
                        "2001-10-31T02:30:00.000-05:00",
                        MockRecord("Hello, world 2!", reply="12345678"),
                        viewer=MockViewer(repost="12345678"),
                    )
                ),
                MockPost(
                    MockPostData(
                        "2001-10-31T01:30:00.000-05:00",
                        MockRecord("Goodbye, world!"),
                        viewer=MockViewer(repost="12345678"),
                    )
                ),
                MockPost(
                    MockPostData(
                        "2001-10-31T01:30:00.000-05:00",
                        MockRecord("I'm still here, world!", langs=["en"]),
                    )
                ),
            ]
        ),
    )
    messages = bluesky.read()
    assert len(messages) == 1
    assert messages[0].message == "I'm still here, world!"
    assert messages[0].language == "en"


def test_bluesky_reconstructs_embeds_successfully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Test that the Bluesky connection reconstructs embeds successfully.
    The test case reproduces a real-world scenario where, when a user posts a message
    that only contains a link, Bluesky can trim the actual URL in the post's message
    and include the full URL in the embed.

    Since we're ignoring the embed in the generic Message, we need to reconstruct
    the URL on the message's text.
    """

    # We need to patch `isinstance` to make our mocked classes work,
    # so we preserve the original `isinstance` function
    original_isinstance = isinstance

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
        "builtins.isinstance",
        lambda obj, cls: (
            True
            if cls == AppBskyEmbedExternal.Main
            and original_isinstance(obj, MockExternalEmbed)
            else original_isinstance(obj, cls)
        ),
    )

    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_args, **_kwargs: MockFeed(
            [
                MockPost(
                    MockPostData(
                        "2000-10-31T01:30:00.000-05:00",
                        MockRecord(
                            "open.spotify.com/track/0ElVpg...",
                            embed=MockExternalEmbed(
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
                            embed=MockExternalEmbed(
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


def test_get_current_indexed_at() -> None:
    """
    Test that `_get_current_indexed_at` returns a timestamp.
    """

    current_time = datetime.now(timezone.utc)
    indexed_at = _get_current_indexed_at()

    # Ensure the returned value is a timestamp
    parsed_time = datetime.fromisoformat(indexed_at)
    assert parsed_time.tzinfo == timezone.utc

    # Ensure the returned timestamp is close to the current time
    delta = abs((parsed_time - current_time).total_seconds())
    assert delta < 1


def test_get_meta_tag_from_html_metadata() -> None:
    """
    Tests to check that the meta tag values are extracted correctly
    from the HTML metadata.
    """

    # Test case 1: Meta tag with the specified property exists
    html_content = """
    <html>
        <head>
            <meta property="og:title" content="Test Title">
            <meta property="og:description" content="Test Description">
        </head>
    </html>
    """
    soup = BeautifulSoup(html_content, "html.parser")
    result = _get_meta_tag_from_html_metadata(soup, "og:title")
    assert result == "Test Title"

    # Test case 2: Meta tag with the specified property does not exist
    result = _get_meta_tag_from_html_metadata(soup, "og:image")
    assert result is None

    # Test case 3: Meta tag with no content attribute
    html_content = """
    <html>
        <head>
            <meta property="og:title">
        </head>
    </html>
    """
    soup = BeautifulSoup(html_content, "html.parser")
    result = _get_meta_tag_from_html_metadata(soup, "og:title")
    assert result is None

    # Test case 4: multiple meta tags with the same property
    html_content = """
    <html>
        <head>
            <meta property="og:title" content="Title 1">
            <meta property="og:title" content="Title 2">
        </head>
    </html>
    """
    soup = BeautifulSoup(html_content, "html.parser")
    result = _get_meta_tag_from_html_metadata(soup, "og:title")
    assert result == "Title 1"


def test_generate_post_embed_and_facets(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test `_generate_post_embed_and_facets` to ensure it correctly generates
    embed objects and facets for links in the text.
    """

    # Setup
    monkeypatch.setattr(
        "barkr.connections.bluesky.Client.login",
        lambda *_: None,
    )

    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_: MockFeed([]),
    )

    connection = BlueskyConnection(
        "BlueskyClass",
        [ConnectionMode.WRITE],
        "test_handle",
        "test_password",
    )

    # Mocking requests
    def mock_requests_get(url: str, _timeout: int, _headers):
        if "valid-url.com" in url:
            html_content = """
            <html>
                <head>
                    <title>Valid URL</title>
                    <meta property="og:description" content="A valid URL description">
                    <meta property="og:image" content="https://valid-url.com/image.jpg">
                </head>
            </html>
            """
            return MockResponse(html_content.encode("utf-8"), 200)

        if "no-meta.com" in url:
            html_content = """
            <html>
                <head>
                    <title>No Meta</title>
                </head>
            </html>
            """
            return MockResponse(html_content.encode("utf-8"), 200)

        return MockResponse(b"", 404)

    def mock_upload_image_url_to_atproto_blob(_self, image_url: str):
        if "valid-url.com/image.jpg" in image_url:
            return BlobRef(ref="mock_blob_ref", mimeType="image/jpeg", size=12345)

        return None

    monkeypatch.setattr("requests.get", mock_requests_get)
    monkeypatch.setattr(
        "barkr.connections.bluesky.BlueskyConnection._upload_image_url_to_atproto_blob",
        mock_upload_image_url_to_atproto_blob,
    )

    # Test case 1: Text with a valid URL
    text = "Check this out: https://valid-url.com"
    embed, facets = (
        connection._generate_post_embed_and_facets(  # pylint: disable=protected-access
            text
        )
    )
    assert embed is not None
    assert embed.external.uri == "https://valid-url.com"
    assert embed.external.title == "Valid URL"
    assert embed.external.description == "A valid URL description"
    assert embed.external.thumb.ref == "mock_blob_ref"
    assert len(facets) == 1
    assert facets[0].features[0].uri == "https://valid-url.com"

    # Test case 2: Text with a URL that has no metadata
    text = "Visit this: https://no-meta.com"
    embed, facets = (
        connection._generate_post_embed_and_facets(  # pylint: disable=protected-access
            text
        )
    )
    assert embed is not None
    assert embed.external.uri == "https://no-meta.com"
    assert embed.external.title == "No Meta"
    assert embed.external.description == "https://no-meta.com"
    assert embed.external.thumb is None
    assert len(facets) == 1
    assert facets[0].features[0].uri == "https://no-meta.com"

    # Test case 3: Text with an invalid URL
    text = "This link is broken: https:/invalid-url.com"
    embed, facets = (
        connection._generate_post_embed_and_facets(  # pylint: disable=protected-access
            text
        )
    )
    assert embed is None
    assert len(facets) == 0

    # Test case 4: Text with multiple URLs
    text = "Multiple links: https://valid-url.com and https://no-meta.com"
    embed, facets = (
        connection._generate_post_embed_and_facets(  # pylint: disable=protected-access
            text
        )
    )
    assert embed is not None
    assert embed.external.uri == "https://valid-url.com"
    assert len(facets) == 2
    assert facets[0].features[0].uri == "https://valid-url.com"
    assert facets[1].features[0].uri == "https://no-meta.com"

    # Test case 5: Text with no URLs
    text = "This text has no links."
    embed, facets = (
        connection._generate_post_embed_and_facets(  # pylint: disable=protected-access
            text
        )
    )
    assert embed is None
    assert len(facets) == 0
