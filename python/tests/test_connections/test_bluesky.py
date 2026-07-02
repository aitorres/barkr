"""
Module to implement unit tests for the Bluesky connection class
"""

import io

import pytest
from atproto_client.exceptions import BadRequestError, NetworkError
from atproto_client.models import (
    AppBskyEmbedExternal,
    AppBskyEmbedImages,
    AppBskyEmbedRecord,
    AppBskyEmbedVideo,
    AppBskyRichtextFacet,
    ComAtprotoRepoStrongRef,
)
from atproto_client.models.blob_ref import BlobRef
from PIL import Image
from requests.exceptions import RequestException
from tests.mocks.bluesky import (
    MockAuthor,
    MockExternal,
    MockExternalEmbed,
    MockFeed,
    MockPost,
    MockPostData,
    MockRecord,
    MockReply,
    MockReplyParent,
    MockResponse,
    MockUploadBlobResponse,
    MockViewer,
)

from barkr.connections import BlueskyConnection, ConnectionMode
from barkr.models import Message


def test_bluesky_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Basic end-to-end reads and filtering behavior."""
    _setup_bluesky_connection_monkeypatch(monkeypatch)
    bluesky_no_initial_messages = _create_test_bluesky_connection()
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

    bluesky = _create_test_bluesky_connection()
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

    bluesky.min_id = None
    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_args, **_kwargs: MockFeed(
            [
                MockPost(
                    MockPostData(
                        "2001-10-31T02:30:00.000-05:00",
                        MockRecord(
                            "This is a quote post!",
                            embed=AppBskyEmbedRecord.Main(
                                record=ComAtprotoRepoStrongRef.Main(
                                    uri="at://did:plc:test/app.bsky.feed.post/quoted",
                                    cid="bafyreirecordcid",
                                )
                            ),
                        ),
                        uri="at://did:plc:test/app.bsky.feed.post/3jzfcijpj2z2f",
                    )
                ),
                MockPost(
                    MockPostData(
                        "2001-10-31T01:30:00.000-05:00",
                        MockRecord("Regular post here!"),
                        uri="at://did:plc:test/app.bsky.feed.post/3jzfcijpj2z2e",
                    )
                ),
            ]
        ),
    )
    messages = bluesky.read()
    assert len(messages) == 1
    assert messages[0].message == "Regular post here!"


def test_bluesky_reconstructs_embeds_successfully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reconstruct trimmed URLs from external embeds when needed."""
    # We need to patch `isinstance` to make our mocked classes work,
    # so we preserve the original `isinstance` function
    original_isinstance = isinstance

    _setup_bluesky_connection_monkeypatch(monkeypatch)
    bsky = _create_test_bluesky_connection()

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


def test_generate_post_embed_and_facets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Generate external embed and URL facets from text."""
    _setup_bluesky_connection_monkeypatch(monkeypatch)
    connection = _create_test_bluesky_connection()

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

    def mock_upload_external_thumb_blob_from_url(_self, image_url: str):
        if "valid-url.com/image.jpg" in image_url:
            return BlobRef(ref="mock_blob_ref", mimeType="image/jpeg", size=12345)

        return None

    monkeypatch.setattr("requests.get", mock_requests_get)
    monkeypatch.setattr(
        "barkr.connections.bluesky.BlueskyConnection"
        "._upload_external_thumb_blob_from_url",
        mock_upload_external_thumb_blob_from_url,
    )

    generate = (
        connection._generate_post_embed_and_facets  # pylint: disable=protected-access
    )

    # Test case 1: Text with a valid URL
    text = "Check this out: https://valid-url.com"
    embed, facets = generate(text)
    assert embed is not None
    assert embed.external.uri == "https://valid-url.com"
    assert embed.external.title == "Valid URL"
    assert embed.external.description == "A valid URL description"
    assert embed.external.thumb is not None
    assert embed.external.thumb.ref == "mock_blob_ref"
    assert len(facets) == 1
    assert isinstance(facets[0].features[0], AppBskyRichtextFacet.Link)
    assert facets[0].features[0].uri == "https://valid-url.com"

    # Test case 2: Text with a URL that has no metadata
    text = "Visit this: https://no-meta.com"
    embed, facets = generate(text)
    assert embed is not None
    assert embed.external.uri == "https://no-meta.com"
    assert embed.external.title == "No Meta"
    assert embed.external.description == "https://no-meta.com"
    assert embed.external.thumb is None
    assert len(facets) == 1
    assert isinstance(facets[0].features[0], AppBskyRichtextFacet.Link)
    assert facets[0].features[0].uri == "https://no-meta.com"

    # Test case 3: Text with an invalid URL
    text = "This link is broken: https:/invalid-url.com"
    embed, facets = generate(text)
    assert embed is None
    assert len(facets) == 0

    # Test case 4: Text with multiple URLs
    text = "Multiple links: https://valid-url.com and https://no-meta.com"
    embed, facets = generate(text)
    assert embed is not None
    assert embed.external.uri == "https://valid-url.com"
    assert len(facets) == 2
    assert isinstance(facets[0].features[0], AppBskyRichtextFacet.Link)
    assert facets[0].features[0].uri == "https://valid-url.com"
    assert isinstance(facets[1].features[0], AppBskyRichtextFacet.Link)
    assert facets[1].features[0].uri == "https://no-meta.com"

    # Test case 5: Text with no URLs
    text = "This text has no links."
    embed, facets = generate(text)
    assert embed is None
    assert len(facets) == 0


def test_generate_post_embed_and_facets_timeout_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recover facets despite metadata timeouts; embed if later URL works."""
    _setup_bluesky_connection_monkeypatch(monkeypatch)
    connection = _create_test_bluesky_connection()

    def mock_upload_external_thumb_blob_from_url(_self, image_url: str):
        if "valid-url.com/image.jpg" in image_url:
            return BlobRef(ref="mock_blob_ref", mimeType="image/jpeg", size=12345)

        return None

    monkeypatch.setattr(
        "barkr.connections.bluesky.BlueskyConnection"
        "._upload_external_thumb_blob_from_url",
        mock_upload_external_thumb_blob_from_url,
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

    generate = (
        connection._generate_post_embed_and_facets  # pylint: disable=protected-access
    )

    text = "Check this out: https://url-that-times-out.com"
    embed, facets = generate(text)
    assert embed is None
    assert len(facets) == 1
    assert isinstance(facets[0].features[0], AppBskyRichtextFacet.Link)
    assert facets[0].features[0].uri == "https://url-that-times-out.com"

    # Test case 2: the first URL times out, but the second one is valid
    # so we should get two facets, and an embed for the second URL
    text = "I have two links: https://url-that-times-out.com and https://valid-url.com"
    embed, facets = generate(text)
    assert embed is not None
    assert embed.external.uri == "https://valid-url.com"
    assert embed.external.title == "Valid URL"
    assert embed.external.description == "A valid URL description"

    assert isinstance(facets[0].features[0], AppBskyRichtextFacet.Link)
    assert facets[0].features[0].uri == "https://url-that-times-out.com"
    assert isinstance(facets[1].features[0], AppBskyRichtextFacet.Link)
    assert facets[1].features[0].uri == "https://valid-url.com"


def test_extract_media_list_from_embed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Extract media bytes and types from supported embed variants."""
    _setup_bluesky_connection_monkeypatch(monkeypatch)
    connection = _create_test_bluesky_connection()

    test_did: str = MockAuthor().did

    extract = (
        connection._extract_media_list_from_embed  # pylint: disable=protected-access
    )

    # Case: empty embed
    assert not extract(test_did, None)

    # Case: non-supported embeds
    assert not extract(
        test_did,
        AppBskyEmbedExternal.Main(
            external=AppBskyEmbedExternal.External(
                uri="https://example.com",
                title="Example Title",
                description="Example Description",
            )
        ),
    )
    assert not extract(
        test_did,
        AppBskyEmbedRecord.Main(
            record=ComAtprotoRepoStrongRef.Main(
                uri="at://example.com",
                cid="example_cid",
            )
        ),
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
    media_list = extract(test_did, video_embed)
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
    media_list = extract(test_did, image_embed)
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
    assert not extract(test_did, video_embed)


def test_upload_external_thumb_blob_from_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fetch image by URL and upload as blob; handle failures."""
    _setup_bluesky_connection_monkeypatch(monkeypatch)

    conn = _create_test_bluesky_connection()

    upload = (
        conn._upload_external_thumb_blob_from_url  # pylint: disable=protected-access
    )

    def create_test_image_bytes() -> bytes:
        output = io.BytesIO()
        Image.new("RGB", (16, 16), color="red").save(output, "JPEG", quality=90)
        return output.getvalue()

    def valid_image_response(response_code: int) -> MockResponse:
        return MockResponse(
            create_test_image_bytes(),
            response_code,
            headers={"Content-Type": "image/jpeg"},
        )

    # Case: Successful image retrieval and upload
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **_kargs: valid_image_response(200),
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

    blob_ref = upload("https://example.com/image.jpg")
    assert blob_ref is not None
    assert blob_ref.ref == "test_ref"
    assert blob_ref.mime_type == "image/jpeg"

    # Case: Failed image retrieval
    def mock_failed_request_get(*_args, **_kwargs):
        raise RequestException("Failed to get image")

    monkeypatch.setattr("requests.get", mock_failed_request_get)

    assert upload("https://example.com/bad-image.jpg") is None

    # Case: Successful image retrieval but failed upload
    monkeypatch.setattr(
        "requests.get", lambda *args, **_kargs: valid_image_response(200)
    )
    monkeypatch.setattr(
        "atproto_client.Client.upload_blob",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(BadRequestError()),
    )

    assert upload("https://example.com/image.jpg") is None

    # Case: Successful retrieval, image is larger than Bluesky limit
    # and compression is disabled
    large_image_data = b"a" * 2_000_000  # 2 MB
    monkeypatch.setattr(
        "requests.get", lambda *args, **_kargs: MockResponse(large_image_data, 200)
    )
    conn.compress_images = False
    assert upload("https://example.com/large-image.jpg") is None

    # Case: successful retrieval, image is larger than Bluesky limit
    # and compression is enabled, but compression fails
    conn.compress_images = True
    monkeypatch.setattr(
        "barkr.connections.bluesky.compress_image_to_size_limit",
        lambda *_args, **_kwargs: None,
    )
    assert upload("https://example.com/large-image.jpg") is None

    # Case: non-200 image URL should be skipped
    monkeypatch.setattr(
        "requests.get", lambda *args, **_kargs: valid_image_response(404)
    )
    assert upload("https://example.com/not-found.jpg") is None

    # Case: non-image payload should be skipped (prevents */* mimeType uploads)
    monkeypatch.setattr(
        "requests.get",
        lambda *args, **_kargs: MockResponse(
            b"<html><body>not an image</body></html>",
            200,
            headers={"Content-Type": "text/html"},
        ),
    )
    assert upload("https://example.com/not-image") is None


def test_bluesky_feed_retry_and_min_id_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry author feed fetches and keep min_id aligned with non-repost posts."""
    _setup_bluesky_connection_monkeypatch(monkeypatch)

    connection = BlueskyConnection(
        "BlueskyClass",
        [ConnectionMode.READ],
        "test_handle",
        "test_password",
    )

    sleep_delays: list[float] = []
    monkeypatch.setattr("time.sleep", sleep_delays.append)

    transient_errors = [NetworkError(), BadRequestError()]
    feed_calls = 0

    def mock_get_author_feed(*_args, **_kwargs):
        nonlocal feed_calls
        feed_calls += 1
        if feed_calls <= len(transient_errors):
            raise transient_errors[feed_calls - 1]

        return MockFeed(
            [
                MockPost(
                    MockPostData(
                        "2000-10-31T01:30:00.000-05:00",
                        MockRecord("Recovered post"),
                        uri="at://did:plc:test/app.bsky.feed.post/recovered",
                    )
                )
            ]
        )

    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        mock_get_author_feed,
    )

    user_feed = (
        connection._get_user_feed_with_retry()  # pylint: disable=protected-access
    )
    assert user_feed is not None
    assert len(user_feed) == 1
    assert sleep_delays == [0.1, 0.2]

    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(BadRequestError()),
    )
    sleep_delays.clear()
    assert (  # pylint: disable=protected-access
        connection._get_user_feed_with_retry() is None
    )
    assert sleep_delays == [0.1, 0.2]


def test_bluesky_repost_as_most_recent_does_not_corrupt_min_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the most recent feed item is a repost from another user whose DID
    sorts lexicographically before the authenticated user's DID, its id will
    forcefully be less than any post of the authenticated user.
    We cannot take that as the min_id for sorting the user's posts.
    Otherwise every subsequent fetch will treat ALL of the user's own posts
    as "new" because their URIs are always greater than the foreign DID prefix,
    causing duplicate message pulls."""

    _setup_bluesky_connection_monkeypatch(monkeypatch)

    own_post_uri = "at://did:plc:zzz/app.bsky.feed.post/3jzfcijpj2z2a"
    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_args, **_kwargs: MockFeed(
            [
                MockPost(
                    MockPostData(
                        "2000-10-31T01:30:00.000-05:00",
                        MockRecord("Initial own post"),
                        uri=own_post_uri,
                    )
                ),
            ]
        ),
    )

    bluesky = BlueskyConnection(
        "BlueskyRepostBug",
        [ConnectionMode.READ],
        "test_handle",
        "test_password",
    )
    assert bluesky.min_id == own_post_uri

    repost_uri = "at://did:plc:aaa/app.bsky.feed.post/3jzfcijpj2z2z"
    new_own_post_uri = "at://did:plc:zzz/app.bsky.feed.post/3jzfcijpj2z2b"
    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_args, **_kwargs: MockFeed(
            [
                # Most recent item is a repost of someone else's post
                MockPost(
                    MockPostData(
                        "2000-11-01T01:00:00.000-05:00",
                        MockRecord("Foreign user's post"),
                        uri=repost_uri,
                        viewer=MockViewer(repost="some-repost-ref"),
                    )
                ),
                MockPost(
                    MockPostData(
                        "2000-10-31T02:30:00.000-05:00",
                        MockRecord("My new post!"),
                        uri=new_own_post_uri,
                    )
                ),
            ]
        ),
    )

    messages = bluesky.read()
    assert len(messages) == 1
    assert messages[0].message == "My new post!"

    assert bluesky.min_id == new_own_post_uri

    messages = bluesky.read()
    assert len(messages) == 0


def test_bluesky_set_min_id_preserves_existing_when_fetch_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If `_get_user_feed_with_retry` returns None (all retries failed),
    `_set_min_id_from_user_feed` must NOT wipe the existing min_id.
    Wiping it would cause the next fetch to re-emit every visible post
    as new, producing duplicate cross-posts."""

    _setup_bluesky_connection_monkeypatch(monkeypatch)
    connection = _create_test_bluesky_connection()

    original_min_id = "at://did:plc:test/app.bsky.feed.post/original"
    connection.min_id = original_min_id

    monkeypatch.setattr(
        BlueskyConnection,
        "_get_user_feed_with_retry",
        lambda *_args: None,
    )

    connection._set_min_id_from_user_feed()  # pylint: disable=protected-access
    assert connection.min_id == original_min_id


def test_bluesky_set_min_id_preserves_existing_when_feed_has_only_reposts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the feed fetch succeeds but contains only reposts, there is no
    own-post URI to use as min_id."""

    _setup_bluesky_connection_monkeypatch(monkeypatch)
    connection = _create_test_bluesky_connection()

    original_min_id = "at://did:plc:test/app.bsky.feed.post/original"
    connection.min_id = original_min_id

    repost_only_feed = [
        MockPost(
            MockPostData(
                "2000-10-31T02:30:00.000-05:00",
                MockRecord("Repost only"),
                uri="at://did:plc:foreign/app.bsky.feed.post/repost",
                viewer=MockViewer(repost="repost-ref"),
            )
        )
    ]
    monkeypatch.setattr(
        BlueskyConnection,
        "_get_user_feed_with_retry",
        lambda *_args: repost_only_feed,
    )

    connection._set_min_id_from_user_feed()  # pylint: disable=protected-access
    assert connection.min_id == original_min_id


def test_bluesky_set_min_id_updates_when_newer_own_post_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sanity check: when the feed fetch succeeds and contains a newer own
    post, min_id is correctly advanced."""

    _setup_bluesky_connection_monkeypatch(monkeypatch)
    connection = _create_test_bluesky_connection()

    connection.min_id = "at://did:plc:test/app.bsky.feed.post/older"

    new_own_uri = "at://did:plc:test/app.bsky.feed.post/newer"
    feed = [
        MockPost(
            MockPostData(
                "2000-10-31T02:30:00.000-05:00",
                MockRecord("New own post"),
                uri=new_own_uri,
            )
        )
    ]
    monkeypatch.setattr(
        BlueskyConnection,
        "_get_user_feed_with_retry",
        lambda *_args: feed,
    )

    connection._set_min_id_from_user_feed()  # pylint: disable=protected-access
    assert connection.min_id == new_own_uri


def test_bluesky_post_recovers_from_network_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A NetworkError (e.g., DNS failure) during send_post should be swallowed
    so the connection can keep running. min_id must be refreshed from the feed
    in case the post actually went through before the network dropped."""

    _setup_bluesky_connection_monkeypatch(monkeypatch)
    bluesky = _create_test_bluesky_connection()

    def raise_network_error(*_args, **_kwargs):
        raise NetworkError("Temporary failure in name resolution")

    monkeypatch.setattr(
        "barkr.connections.bluesky.Client.send_post", raise_network_error
    )

    set_min_id_calls: list[bool] = []
    monkeypatch.setattr(
        BlueskyConnection,
        "_set_min_id_from_user_feed",
        lambda self: set_min_id_calls.append(True),
    )

    posted = bluesky._post(  # pylint: disable=protected-access
        [
            Message(
                id="ForeignId1", message="test message 1", source_connection="test"
            ),
            Message(
                id="ForeignId2", message="test message 2", source_connection="test"
            ),
        ]
    )

    assert not posted
    assert set_min_id_calls == [True, True]


def test_bluesky_post_network_error_preserves_min_id_when_recovery_feed_fetch_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When `send_post` raises NetworkError, the connection calls
    `_set_min_id_from_user_feed` to recover. If the recovery feed fetch
    ALSO fails, the pre-existing min_id must be preserved.
    """

    _setup_bluesky_connection_monkeypatch(monkeypatch)
    connection = _create_test_bluesky_connection()

    original_min_id = "at://did:plc:test/app.bsky.feed.post/before_failure"
    connection.min_id = original_min_id

    def raise_network_error(*_args, **_kwargs):
        raise NetworkError("Temporary failure in name resolution")

    monkeypatch.setattr(
        "barkr.connections.bluesky.Client.send_post", raise_network_error
    )
    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        raise_network_error,
    )
    # Skip the retry sleeps to keep the test fast.
    monkeypatch.setattr("time.sleep", lambda _delay: None)

    posted = connection._post(  # pylint: disable=protected-access
        [Message(id="src-1", message="msg", source_connection="test")]
    )

    assert not posted
    assert connection.min_id == original_min_id


def test_bluesky_post_network_error_preserves_min_id_with_repost_only_recovery_feed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same regression as above, but the recovery feed fetch succeeds with
    a feed that contains only reposts. min_id must still be preserved."""

    _setup_bluesky_connection_monkeypatch(monkeypatch)
    connection = _create_test_bluesky_connection()

    original_min_id = "at://did:plc:test/app.bsky.feed.post/before_failure"
    connection.min_id = original_min_id

    monkeypatch.setattr(
        "barkr.connections.bluesky.Client.send_post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(NetworkError()),
    )
    monkeypatch.setattr(
        "atproto_client.namespaces.sync_ns.AppBskyFeedNamespace.get_author_feed",
        lambda *_args, **_kwargs: MockFeed(
            [
                MockPost(
                    MockPostData(
                        "2000-10-31T02:30:00.000-05:00",
                        MockRecord("Foreign repost"),
                        uri="at://did:plc:foreign/app.bsky.feed.post/repost",
                        viewer=MockViewer(repost="repost-ref"),
                    )
                )
            ]
        ),
    )

    posted = connection._post(  # pylint: disable=protected-access
        [Message(id="src-1", message="msg", source_connection="test")]
    )

    assert not posted
    assert connection.min_id == original_min_id


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


def _create_test_bluesky_connection() -> BlueskyConnection:
    """Returns a valid instance of BlueskyConnection for tests"""
    return BlueskyConnection(
        "BlueskyClass",
        [ConnectionMode.READ, ConnectionMode.WRITE],
        "test_handle",
        "test_password",
    )
