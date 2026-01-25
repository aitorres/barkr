"""
Module to implement unit tests for the Bluesky connection class
"""

import io
from dataclasses import dataclass
from typing import Optional

import pytest
from atproto_client.exceptions import BadRequestError  # type: ignore
from atproto_client.models import (  # type: ignore
    AppBskyEmbedExternal,
    AppBskyEmbedImages,
    AppBskyEmbedRecord,
    AppBskyEmbedRecordWithMedia,
    AppBskyEmbedVideo,
    ComAtprotoRepoStrongRef,
)
from atproto_client.models.blob_ref import BlobRef  # type: ignore
from bs4 import BeautifulSoup
from PIL import Image
from requests.exceptions import RequestException

from barkr.connections import BlueskyConnection, ConnectionMode
from barkr.connections.bluesky import (
    _get_meta_tag_from_html_metadata,
    _is_quote_embed,
)


@dataclass(frozen=True)
class MockUploadBlobResponse:
    """Mock response for Client.upload_blob."""

    blob: BlobRef


@dataclass(frozen=True)
class MockResponse:
    """Minimal HTTP response mock (content + status)."""

    content: bytes
    status_code: int


@dataclass(frozen=True)
class MockExternal:
    """Represents a Bluesky external embed payload."""

    title: str
    uri: str
    description: str


@dataclass(frozen=True)
class MockExternalEmbed:
    """Container for external embed in mocked posts."""

    external: Optional[MockExternal] = None


@dataclass(frozen=True)
class MockReplyParent:
    """Mock reply parent with URI."""

    uri: str


@dataclass(frozen=True)
class MockReply:
    """Mock reply structure with parent."""

    parent: MockReplyParent


@dataclass(frozen=True)
class MockRecord:
    """Mock Bluesky record with text, reply, embed and langs."""

    text: str
    reply: Optional[MockReply] = None
    embed: Optional[MockExternalEmbed] = None
    langs: Optional[list[str]] = None


@dataclass(frozen=True)
class MockViewer:
    """Mock viewer info; only 'repost' is relevant here."""

    # NOTE: this is not a string in the real contract, but enough
    # for our tests
    repost: Optional[str] = None


@dataclass(frozen=True)
class MockAuthor:
    """Mock author with a default DID."""

    did: str = "did:plc:z72i7hdynmk6r22z27h6tvur"


@dataclass(frozen=True)
class MockPostData:
    """Post wrapper carrying indexed_at, record, author and viewer."""

    indexed_at: str
    record: MockRecord
    uri: str = "at://did:plc:test/app.bsky.feed.post/testid123"
    author: MockAuthor = MockAuthor()
    viewer: Optional[MockViewer] = None


@dataclass(frozen=True)
class MockPost:
    """Envelope for a single feed item."""

    post: MockPostData


@dataclass(frozen=True)
class MockFeed:
    """Feed response containing a list of posts."""

    feed: list[MockPost]


def test_bluesky_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Basic end-to-end reads and filtering behavior."""
    _setup_bluesky_connection_monkeypatch(monkeypatch)

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
                        "2000-10-31T01:30:00.000-05:00",
                        MockRecord("Hello, world!"),
                        uri="at://did:plc:test/app.bsky.feed.post/3jzfcijpj2z2b",
                    )
                ),
                MockPost(
                    MockPostData(
                        "2000-10-29T01:30:00.000-05:00",
                        MockRecord("Goodbye, world!"),
                        uri="at://did:plc:test/app.bsky.feed.post/3jzfcijpj2z2a",
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
    assert bluesky.min_id == "at://did:plc:test/app.bsky.feed.post/3jzfcijpj2z2b"

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
                        "2000-10-31T02:30:00.000-05:00",
                        MockRecord("Hello, world 2!"),
                        uri="at://did:plc:test/app.bsky.feed.post/3jzfcijpj2z2c",
                    )
                ),
                MockPost(
                    MockPostData(
                        "2000-10-31T01:30:00.000-05:00",
                        MockRecord("Goodbye, world!"),
                        uri="at://did:plc:test/app.bsky.feed.post/3jzfcijpj2z2b",
                    )
                ),
            ]
        ),
    )
    messages = bluesky.read()
    assert len(messages) == 1
    assert messages[0].message == "Hello, world 2!"
    assert messages[0].id == "at://did:plc:test/app.bsky.feed.post/3jzfcijpj2z2c"
    assert messages[0].metadata.language is None

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
                        MockRecord(
                            "Hello, world 2!",
                            reply=MockReply(
                                MockReplyParent(
                                    "at://did:plc:test/app.bsky.feed.post/12345678"
                                )
                            ),
                        ),
                        uri="at://did:plc:test/app.bsky.feed.post/3jzfcijpj2z2d",
                    )
                ),
            ]
        ),
    )
    messages = bluesky.read()
    assert len(messages) == 1
    assert messages[0].reply_to_id == "at://did:plc:test/app.bsky.feed.post/12345678"

    # Testing that Bluesky ignores posts that are reposts
    bluesky.min_id = None
    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_args, **_kwargs: MockFeed(
            [
                MockPost(
                    MockPostData(
                        "2001-10-31T02:30:00.000-05:00",
                        MockRecord(
                            "Hello, world 2!",
                            reply=MockReply(
                                MockReplyParent(
                                    "at://did:plc:test/app.bsky.feed.post/12345678"
                                )
                            ),
                        ),
                        uri="at://did:plc:test/app.bsky.feed.post/3jzfcijpj2z2e",
                        viewer=MockViewer(repost="12345678"),
                    )
                ),
                MockPost(
                    MockPostData(
                        "2001-10-31T01:30:00.000-05:00",
                        MockRecord("Goodbye, world!"),
                        uri="at://did:plc:test/app.bsky.feed.post/3jzfcijpj2z2d",
                        viewer=MockViewer(repost="12345678"),
                    )
                ),
                MockPost(
                    MockPostData(
                        "2001-10-31T01:30:00.000-05:00",
                        MockRecord("I'm still here, world!", langs=["en"]),
                        uri="at://did:plc:test/app.bsky.feed.post/3jzfcijpj2z2c",
                    )
                ),
            ]
        ),
    )
    messages = bluesky.read()
    assert len(messages) == 1
    assert messages[0].message == "I'm still here, world!"
    assert messages[0].metadata.language == "en"


def test_bluesky_reconstructs_embeds_successfully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reconstruct trimmed URLs from external embeds when needed."""
    # We need to patch `isinstance` to make our mocked classes work,
    # so we preserve the original `isinstance` function
    original_isinstance = isinstance

    _setup_bluesky_connection_monkeypatch(monkeypatch)

    bsky = BlueskyConnection(
        "BlueskyClass",
        [ConnectionMode.READ],
        "test_handle",
        "test_password",
    )

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
                        uri="at://did:plc:test/app.bsky.feed.post/3jzfcijpj2z2a",
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
                        uri="at://did:plc:test/app.bsky.feed.post/3jzfcijpj2z2b",
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


def test_get_meta_tag_from_html_metadata() -> None:
    """Extract meta tag values from small HTML snippets."""
    # Test case 1: Meta tag with the specified property exists
    html_content = (
        "<html><head><meta property='og:title' content='Test Title'>"
        "<meta property='og:description' content='Test Description'></head></html>"
    )
    soup = BeautifulSoup(html_content, "html.parser")
    result = _get_meta_tag_from_html_metadata(soup, "og:title")
    assert result == "Test Title"

    # Test case 2: Meta tag with the specified property does not exist
    result = _get_meta_tag_from_html_metadata(soup, "og:image")
    assert result is None

    # Test case 3: Meta tag with no content attribute
    html_content = "<html><head><meta property='og:title'></head></html>"
    soup = BeautifulSoup(html_content, "html.parser")
    result = _get_meta_tag_from_html_metadata(soup, "og:title")
    assert result is None

    # Test case 4: multiple meta tags with the same property
    html_content = (
        "<html><head><meta property='og:title' content='Title 1'>"
        "<meta property='og:title' content='Title 2'></head></html>"
    )
    soup = BeautifulSoup(html_content, "html.parser")
    result = _get_meta_tag_from_html_metadata(soup, "og:title")
    assert result == "Title 1"


def test_generate_post_embed_and_facets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Generate external embed and URL facets from text."""
    _setup_bluesky_connection_monkeypatch(monkeypatch)

    connection = BlueskyConnection(
        "BlueskyClass",
        [ConnectionMode.WRITE],
        "test_handle",
        "test_password",
    )

    def mock_requests_get(url: str, *_args, **_kwargs):
        if "valid-url.com" in url:
            html_content = (
                "<html><head><title>Valid URL</title>"
                "<meta property='og:description' content='A valid URL description'>"
                "<meta property='og:image' content='https://valid-url.com/image.jpg'>"
                "</head></html>"
            )
            return MockResponse(html_content.encode("utf-8"), 200)

        if "no-meta.com" in url:
            html_content = "<html><head><title>No Meta</title></head></html>"
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


def test_generate_post_embed_and_facets_timeout_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recover facets despite metadata timeouts; embed if later URL works."""
    _setup_bluesky_connection_monkeypatch(monkeypatch)

    connection = BlueskyConnection(
        "BlueskyClass",
        [ConnectionMode.WRITE],
        "test_handle",
        "test_password",
    )

    def mock_upload_image_url_to_atproto_blob(_self, image_url: str):
        if "valid-url.com/image.jpg" in image_url:
            return BlobRef(ref="mock_blob_ref", mimeType="image/jpeg", size=12345)

        return None

    monkeypatch.setattr(
        "barkr.connections.bluesky.BlueskyConnection._upload_image_url_to_atproto_blob",
        mock_upload_image_url_to_atproto_blob,
    )

    # Test case 1: request fails, but we still want to get the URL facet
    def mock_requests_get_fail(url: str, *_args, **_kwargs):
        if "url-that-times-out.com" in url:
            raise RequestException("Failed to fetch metadata")

        html_content = (
            "<html><head><title>Valid URL</title>"
            "<meta property='og:description' content='A valid URL description'>"
            "<meta property='og:image' content='https://valid-url.com/image.jpg'>"
            "</head></html>"
        )
        return MockResponse(html_content.encode("utf-8"), 200)

    monkeypatch.setattr("requests.get", mock_requests_get_fail)

    text = "Check this out: https://url-that-times-out.com"
    embed, facets = (
        connection._generate_post_embed_and_facets(  # pylint: disable=protected-access
            text
        )
    )
    assert embed is None
    assert len(facets) == 1
    assert facets[0].features[0].uri == "https://url-that-times-out.com"

    # Test case 2: the first URL times out, but the second one is valid
    # so we should get two facets, and an embed for the second URL
    text = "I have two links: https://url-that-times-out.com and https://valid-url.com"
    embed, facets = (
        connection._generate_post_embed_and_facets(  # pylint: disable=protected-access
            text
        )
    )
    assert embed is not None
    assert embed.external.uri == "https://valid-url.com"
    assert embed.external.title == "Valid URL"
    assert embed.external.description == "A valid URL description"

    assert facets[0].features[0].uri == "https://url-that-times-out.com"
    assert facets[1].features[0].uri == "https://valid-url.com"


def test_extract_media_list_from_embed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Extract media bytes and types from supported embed variants."""
    _setup_bluesky_connection_monkeypatch(monkeypatch)

    connection = BlueskyConnection(
        "BlueskyClass",
        [ConnectionMode.READ, ConnectionMode.WRITE],
        "test_handle",
        "test_password",
    )

    test_did: str = MockAuthor().did

    # Case: empty embed
    assert (  # pylint: disable=protected-access
        not connection._extract_media_list_from_embed(test_did, None)
    )

    # Case: non-supported embeds
    assert (  # pylint: disable=protected-access
        not connection._extract_media_list_from_embed(
            test_did,
            AppBskyEmbedExternal.Main(
                external=AppBskyEmbedExternal.External(
                    uri="https://example.com",
                    title="Example Title",
                    description="Example Description",
                )
            ),
        )
    )
    assert (  # pylint: disable=protected-access
        not connection._extract_media_list_from_embed(
            test_did,
            AppBskyEmbedRecord.Main(
                record=ComAtprotoRepoStrongRef.Main(
                    uri="at://example.com",
                    cid="example_cid",
                )
            ),
        )
    )

    # Case: video embed
    monkeypatch.setattr(
        "barkr.connections.bluesky.ComAtprotoSyncNamespace.get_blob",
        lambda *_args, **_kwargs: b"test data",
    )

    video_embed = AppBskyEmbedVideo.Main(
        video=BlobRef(
            ref="bafkreieivl7kursm2qlzlzfq7ktt7f7nvsx7pfgggxerfgnaoim75buopy",
            mimeType="video/mp4",
            size=12345,
        ),
    )
    media_list = (
        connection._extract_media_list_from_embed(  # pylint: disable=protected-access
            test_did, video_embed
        )
    )
    assert len(media_list) == 1
    assert media_list[0].mime_type == "video/mp4"
    assert media_list[0].content == b"test data"

    # Case: image embed
    image_embed = AppBskyEmbedImages.Main(
        images=[
            AppBskyEmbedImages.Image(
                alt="Image 1",
                image=BlobRef(
                    ref="bafkreieivl7kursm2qlzlzfq7ktt7f7nvsx7pfgggxerfgnaoim75buopy",
                    mimeType="image/jpeg",
                    size=12345,
                ),
            ),
            AppBskyEmbedImages.Image(
                alt="Image 2",
                image=BlobRef(
                    ref="bafkreieivl7kursm2qlzlzfq7ktt7f7nvsx7pfgggxerfgnaoim75buopy",
                    mimeType="image/png",
                    size=67890,
                ),
            ),
        ],
    )
    media_list = (
        connection._extract_media_list_from_embed(  # pylint: disable=protected-access
            test_did, image_embed
        )
    )
    assert len(media_list) == 2
    assert media_list[0].mime_type == "image/jpeg"
    assert media_list[1].mime_type == "image/png"

    # Case: exception when getting blob
    monkeypatch.setattr(
        "barkr.connections.bluesky.ComAtprotoSyncNamespace.get_blob",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(BadRequestError()),
    )
    video_embed = AppBskyEmbedVideo.Main(
        video=BlobRef(
            ref="bafkreieivl7kursm2qlzlzfq7ktt7f7nvsx7pfgggxerfgnaoim75buopy",
            mimeType="video/mp4",
            size=12345,
        ),
    )
    assert not connection._extract_media_list_from_embed(  # pylint: disable=protected-access # noqa: E501
        test_did, video_embed
    )


def test_upload_image_url_to_atproto_blob(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fetch image by URL and upload as blob; handle failures."""
    _setup_bluesky_connection_monkeypatch(monkeypatch)

    conn = BlueskyConnection(
        "BlueskyClass",
        [ConnectionMode.WRITE],
        "test_handle",
        "test_password",
    )

    # Case: Successful image retrieval and upload
    monkeypatch.setattr(
        "requests.get", lambda *args, **_kargs: MockResponse(b"image_content", 200)
    )
    monkeypatch.setattr(
        "atproto_client.Client.upload_blob",
        lambda *_args, **_kwargs: MockUploadBlobResponse(
            BlobRef(
                ref="test_ref",
                mimeType="image/jpeg",
                size=123,
            )
        ),
    )

    blob_ref = (
        conn._upload_image_url_to_atproto_blob(  # pylint: disable=protected-access
            "https://example.com/image.jpg"
        )
    )
    assert blob_ref is not None
    assert blob_ref.ref == "test_ref"
    assert blob_ref.mime_type == "image/jpeg"

    # Case: Failed image retrieval
    def mock_failed_request_get(*_args, **_kwargs):
        raise RequestException("Failed to get image")

    monkeypatch.setattr("requests.get", mock_failed_request_get)

    assert (
        conn._upload_image_url_to_atproto_blob(  # pylint: disable=protected-access
            "https://example.com/bad-image.jpg"
        )
        is None
    )

    # Case: Successful image retrieval but failed upload
    monkeypatch.setattr(
        "requests.get", lambda *args, **_kargs: MockResponse(b"image_content", 200)
    )
    monkeypatch.setattr(
        "atproto_client.Client.upload_blob",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(BadRequestError()),
    )

    assert (
        conn._upload_image_url_to_atproto_blob(  # pylint: disable=protected-access
            "https://example.com/image.jpg"
        )
    ) is None

    # Case: Successful retrieval, image is larger than Bluesky limit
    # and compression is disabled
    large_image_data = b"a" * 2_000_000  # 2 MB
    monkeypatch.setattr(
        "requests.get", lambda *args, **_kargs: MockResponse(large_image_data, 200)
    )
    conn.compress_images = False
    assert (
        conn._upload_image_url_to_atproto_blob(  # pylint: disable=protected-access
            "https://example.com/large-image.jpg"
        )
    ) is None

    # Case: successful retrieval, image is larger than Bluesky limit
    # and compression is enabled, but compression fails
    conn.compress_images = True
    monkeypatch.setattr(
        "barkr.connections.bluesky.BlueskyConnection._compress_image",
        lambda *_args, **_kwargs: None,
    )
    assert (
        conn._upload_image_url_to_atproto_blob(  # pylint: disable=protected-access
            "https://example.com/large-image.jpg"
        )
    ) is None


def test_compress_image(monkeypatch: pytest.MonkeyPatch) -> None:
    """Compress large images under Bluesky size limit when enabled."""
    _setup_bluesky_connection_monkeypatch(monkeypatch)
    connection = BlueskyConnection(
        "BlueskyClass",
        [ConnectionMode.WRITE],
        "test_handle",
        "test_password",
        compress_images=True,
    )

    def create_test_image(w: int, h: int) -> bytes:
        output = io.BytesIO()
        Image.new("RGB", (w, h), color="red").save(output, "JPEG", quality=95)
        return output.getvalue()

    # Test case: small-enough image, no compression needed
    small_image_data = create_test_image(100, 100)
    assert len(small_image_data) <= 1000000

    result = connection._compress_image(  # pylint: disable=protected-access
        small_image_data
    )
    assert result is not None
    assert len(result) <= 1000000

    # Test case: Invalid image data
    invalid_image_data = b"not an image"
    assert (
        connection._compress_image(  # pylint: disable=protected-access
            invalid_image_data
        )
        is None
    )

    # Test case: Image.open raises an exception
    def mock_image_open(*args, **kwargs):
        raise ValueError("Invalid image")

    monkeypatch.setattr("PIL.Image.open", mock_image_open)

    valid_image_data = create_test_image(500, 500)
    assert (
        connection._compress_image(valid_image_data)  # pylint: disable=protected-access
        is None
    )


def _setup_bluesky_connection_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Common monkeypatches to avoid real API calls."""
    monkeypatch.setattr(
        "barkr.connections.bluesky.Client.login",
        lambda *_: None,
    )

    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_: MockFeed([]),
    )


def test_is_quote_embed() -> None:
    """Identify quote-embed types vs. other embed variants."""
    assert _is_quote_embed(None) is False

    external_embed = AppBskyEmbedExternal.Main(
        external=AppBskyEmbedExternal.External(
            uri="https://example.com",
            title="Example Title",
            description="Example Description",
        )
    )
    assert _is_quote_embed(external_embed) is False

    images_embed = AppBskyEmbedImages.Main(
        images=[
            AppBskyEmbedImages.Image(
                alt="Image 1",
                image=BlobRef(
                    ref="bafkreihash",
                    mimeType="image/jpeg",
                    size=12345,
                ),
            )
        ]
    )
    assert _is_quote_embed(images_embed) is False

    video_embed = AppBskyEmbedVideo.Main(
        video=BlobRef(
            ref="bafkreiothervid",
            mimeType="video/mp4",
            size=67890,
        )
    )
    assert _is_quote_embed(video_embed) is False

    record_embed = AppBskyEmbedRecord.Main(
        record=ComAtprotoRepoStrongRef.Main(
            uri="at://did:plc:test/app.bsky.feed.post/abc123",
            cid="bafyreirecordcid",
        )
    )
    assert _is_quote_embed(record_embed) is True

    record_with_media_embed = AppBskyEmbedRecordWithMedia.Main(
        record=AppBskyEmbedRecord.Main(
            record=ComAtprotoRepoStrongRef.Main(
                uri="at://did:plc:test/app.bsky.feed.post/xyz789",
                cid="bafyreirecordwithmediacid",
            )
        ),
        media=images_embed,
    )
    assert _is_quote_embed(record_with_media_embed) is True
