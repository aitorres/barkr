"""
Mocks and test data structures for Bluesky connection tests.
Moved to their own file to reduce length and complexity of test_bluesky.py
"""

from dataclasses import dataclass
from typing import Any, Optional, Union

from atproto_client.models.blob_ref import BlobRef


@dataclass(frozen=True)
class MockUploadBlobResponse:
    """Mock response for Client.upload_blob."""

    blob: BlobRef


@dataclass(frozen=True)
class MockResponse:
    """Minimal HTTP response mock (content + status)."""

    content: bytes
    status_code: int
    headers: Optional[dict[str, str]] = None


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
    embed: Union[MockExternalEmbed, Any, None] = None
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
