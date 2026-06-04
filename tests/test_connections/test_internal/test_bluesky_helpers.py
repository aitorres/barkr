"""
Unit tests for Bluesky stateless helpers.
"""

from atproto_client.models import (
    AppBskyEmbedExternal,
    AppBskyEmbedImages,
    AppBskyEmbedRecord,
    AppBskyEmbedRecordWithMedia,
    AppBskyEmbedVideo,
    ComAtprotoRepoStrongRef,
)
from atproto_client.models.blob_ref import BlobRef
from bs4 import BeautifulSoup

from barkr.connections.internal.bluesky_helpers import (
    get_meta_tag_from_html_metadata,
    is_quote_embed,
    process_text_with_embed,
)


def test_get_meta_tag_from_html_metadata() -> None:
    """Extract meta tag values from small HTML snippets."""
    # Test case 1: Meta tag with the specified property exists
    html_content = (
        "<html><head><meta property='og:title' content='Test Title'>"
        "<meta property='og:description' content='Test Description'></head></html>"
    )
    soup = BeautifulSoup(html_content, "html.parser")
    result = get_meta_tag_from_html_metadata(soup, "og:title")
    assert result == "Test Title"

    # Test case 2: Meta tag with the specified property does not exist
    result = get_meta_tag_from_html_metadata(soup, "og:image")
    assert result is None

    # Test case 3: Meta tag with no content attribute
    html_content = "<html><head><meta property='og:title'></head></html>"
    soup = BeautifulSoup(html_content, "html.parser")
    result = get_meta_tag_from_html_metadata(soup, "og:title")
    assert result is None

    # Test case 4: multiple meta tags with the same property
    html_content = (
        "<html><head><meta property='og:title' content='Title 1'>"
        "<meta property='og:title' content='Title 2'></head></html>"
    )
    soup = BeautifulSoup(html_content, "html.parser")
    result = get_meta_tag_from_html_metadata(soup, "og:title")
    assert result == "Title 1"


def test_is_quote_embed() -> None:
    """Identify quote-embed types vs. other embed variants."""
    assert is_quote_embed(None) is False

    external_embed = AppBskyEmbedExternal.Main(
        external=AppBskyEmbedExternal.External(
            uri="https://example.com",
            title="Example Title",
            description="Example Description",
        )
    )
    assert is_quote_embed(external_embed) is False

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
    assert is_quote_embed(images_embed) is False

    video_embed = AppBskyEmbedVideo.Main(
        video=BlobRef(
            ref="bafkreiothervid",
            mimeType="video/mp4",
            size=67890,
        )
    )
    assert is_quote_embed(video_embed) is False

    record_embed = AppBskyEmbedRecord.Main(
        record=ComAtprotoRepoStrongRef.Main(
            uri="at://did:plc:test/app.bsky.feed.post/abc123",
            cid="bafyreirecordcid",
        )
    )
    assert is_quote_embed(record_embed) is True

    record_with_media_embed = AppBskyEmbedRecordWithMedia.Main(
        record=AppBskyEmbedRecord.Main(
            record=ComAtprotoRepoStrongRef.Main(
                uri="at://did:plc:test/app.bsky.feed.post/xyz789",
                cid="bafyreirecordwithmediacid",
            )
        ),
        media=images_embed,
    )
    assert is_quote_embed(record_with_media_embed) is True


def test_process_text_with_embed_returns_original_when_not_expandable() -> None:
    """Leave text untouched when embed is missing, unsupported, or unmatched."""
    original_text = "zzqv zzqx zzqy"
    assert process_text_with_embed(original_text, None) == original_text

    unsupported_embed = AppBskyEmbedImages.Main(
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
    assert process_text_with_embed(original_text, unsupported_embed) == original_text

    external_embed = AppBskyEmbedExternal.Main(
        external=AppBskyEmbedExternal.External(
            uri="https://example.com/fully-different-link",
            title="Example",
            description="Example",
        )
    )
    assert process_text_with_embed(original_text, external_embed) == original_text
