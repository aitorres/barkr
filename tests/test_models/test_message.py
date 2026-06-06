"""
Module to implement unit tests for the Message class.
"""

from barkr.models.media import Media
from barkr.models.mention_style import MentionStyle
from barkr.models.message import Message
from barkr.models.message_allowed_replies import MessageAllowedReplies
from barkr.models.message_mention import MessageMention
from barkr.models.message_metadata import MessageMetadata
from barkr.models.message_type import MessageType
from barkr.models.message_visibility import MessageVisibility


def test_message() -> None:
    """
    Test that the Message class is initialized correctly
    """

    message_1 = Message(
        id="12345",
        message="Hello, world!",
        metadata=MessageMetadata(language="en", label="greeting"),
        source_connection="test",
    )

    assert message_1.id == "12345"
    assert message_1.message == "Hello, world!"
    assert message_1.metadata.language == "en"
    assert message_1.metadata.label == "greeting"
    assert message_1.metadata.visibility == MessageVisibility.PUBLIC
    assert message_1.metadata.allowed_replies is None
    assert message_1.source_connection == "test"
    assert message_1.reply_to_id is None

    message_2 = Message(
        id="67890",
        message="Bonjour le monde!",
        source_connection="test",
    )
    assert message_2.id == "67890"
    assert message_2.message == "Bonjour le monde!"
    assert message_2.metadata.language is None
    assert message_2.metadata.label is None
    assert message_2.metadata.visibility == MessageVisibility.PUBLIC
    assert message_2.metadata.allowed_replies is None
    assert message_2.source_connection == "test"
    assert message_2.reply_to_id is None

    message_3 = Message(
        id="abcde",
        message="Hola, mundo!",
        metadata=MessageMetadata(
            visibility=MessageVisibility.PRIVATE,
            allowed_replies=[MessageAllowedReplies.FOLLOWERS],
        ),
        source_connection="test",
    )
    assert message_3.id == "abcde"
    assert message_3.message == "Hola, mundo!"
    assert message_3.metadata.language is None
    assert message_3.metadata.label is None
    assert message_3.metadata.visibility == MessageVisibility.PRIVATE
    assert message_3.metadata.allowed_replies == [MessageAllowedReplies.FOLLOWERS]
    assert message_3.source_connection == "test"
    assert message_3.reply_to_id is None


def test_message_has_content() -> None:
    """
    Test that the has_content method appropriately
    tells if the Message contains content or not.
    """

    # Base case: check is done for a text-only connection
    assert Message(
        id="12345", message="Hello, world!", source_connection="test"
    ).has_content(MessageType.TEXT_ONLY)
    assert not Message(id="12345", message="", source_connection="test").has_content(
        MessageType.TEXT_ONLY
    )
    assert not Message(id="12345", message="   ", source_connection="test").has_content(
        MessageType.TEXT_ONLY
    )
    assert not Message(id="12345", message="\n", source_connection="test").has_content(
        MessageType.TEXT_ONLY
    )
    assert Message(
        id="12345",
        message="Hello, world!",
        metadata=MessageMetadata(label="greeting"),
        source_connection="test",
    ).has_content(MessageType.TEXT_ONLY)

    # Check for a message with a media object
    media_list = [
        Media(mime_type="image/jpeg", content=b"image data"),
        Media(mime_type="video/mp4", content=b"video data"),
    ]
    assert Message(
        id="12345", message="Hello, world!", media=media_list, source_connection="test"
    ).has_content(MessageType.TEXT_MEDIA)
    assert Message(
        id="12345", message="", media=media_list, source_connection="test"
    ).has_content(MessageType.TEXT_MEDIA)
    assert Message(
        id="12345", message="   ", media=media_list, source_connection="test"
    ).has_content(MessageType.TEXT_MEDIA)
    assert Message(
        id="12345", message="\n", media=media_list, source_connection="test"
    ).has_content(MessageType.TEXT_MEDIA)

    invalid_media_list = [
        Media(mime_type="text/plain", content=b"invalid media"),
        Media(mime_type="application/json", content=b"invalid media"),
    ]
    assert Message(
        id="12345",
        message="Hello, world!",
        media=invalid_media_list,
        source_connection="test",
    ).has_content(MessageType.TEXT_MEDIA)
    assert not Message(
        id="12345", message="", media=invalid_media_list, source_connection="test"
    ).has_content(MessageType.TEXT_MEDIA)
    assert not Message(
        id="12345", message="   ", media=invalid_media_list, source_connection="test"
    ).has_content(MessageType.TEXT_MEDIA)

    empty_media_list: list[Media] = []
    assert Message(
        id="12345",
        message="Hello, world!",
        media=empty_media_list,
        source_connection="test",
    ).has_content(MessageType.TEXT_MEDIA)
    assert not Message(
        id="12345", message="", media=empty_media_list, source_connection="test"
    ).has_content(MessageType.TEXT_MEDIA)
    assert not Message(
        id="12345", message="   ", media=empty_media_list, source_connection="test"
    ).has_content(MessageType.TEXT_MEDIA)

    # We skip messages that have private or direct visibility,
    # even if they have content.
    assert not Message(
        id="12345",
        message="Hello, world!",
        metadata=MessageMetadata(visibility=MessageVisibility.PRIVATE),
        source_connection="test",
    ).has_content(MessageType.TEXT_ONLY)
    assert not Message(
        id="12345",
        message="Hello, world!",
        metadata=MessageMetadata(visibility=MessageVisibility.DIRECT),
        source_connection="test",
    ).has_content(MessageType.TEXT_ONLY)

    # Test with a message that has no content but is private
    assert not Message(
        id="12345",
        message="",
        metadata=MessageMetadata(visibility=MessageVisibility.PRIVATE),
        source_connection="test",
    ).has_content(MessageType.TEXT_ONLY)


def test_message_and_metadata_use_slots() -> None:
    """
    Message and MessageMetadata must remain slotted dataclasses
    (no per-instance __dict__).
    """

    message = Message(id="1", message="hi", source_connection="test")
    metadata = MessageMetadata()

    assert hasattr(Message, "__slots__")
    assert not hasattr(message, "__dict__")

    assert hasattr(MessageMetadata, "__slots__")
    assert not hasattr(metadata, "__dict__")


def test_default_message_metadata_is_shared_singleton() -> None:
    """
    Messages that are initialized without an explicit metadata should share
    the same default MessageMetadata instance.
    """

    # Shared default metadata instance
    message_a = Message(id="a", message="hello", source_connection="test")
    message_b = Message(id="b", message="world", source_connection="test")

    assert message_a.metadata is message_b.metadata

    expected = MessageMetadata()
    assert message_a.metadata == expected
    assert message_a.metadata.language is None
    assert message_a.metadata.label is None
    assert message_a.metadata.visibility == MessageVisibility.PUBLIC
    assert message_a.metadata.allowed_replies is None

    # Custom metadata instance
    custom = MessageMetadata(language="en")
    message_c = Message(id="c", message="hi", source_connection="test", metadata=custom)
    assert message_c.metadata is custom
    assert message_c.metadata is not message_a.metadata


def test_get_content_plain_returns_message_unchanged() -> None:
    """
    `MentionStyle.PLAIN` (default) returns the original body verbatim,
    even when mentions are attached.
    """

    text = "Hello @alice.bsky.social!"
    message = Message(
        id="1",
        message=text,
        source_connection="test",
        metadata=MessageMetadata(
            mentions=[
                MessageMention(
                    url="https://bsky.app/profile/did:plc:alice",
                    username="@alice.bsky.social",
                ),
            ],
        ),
    )

    assert message.get_content() == text
    assert message.get_content(MentionStyle.PLAIN) == text


def test_get_content_short_circuits_without_mentions() -> None:
    """
    Without mentions on the metadata, every style returns the body verbatim.
    """

    text = "Hello, world!"
    message = Message(id="1", message=text, source_connection="test")

    assert message.get_content(MentionStyle.APPEND_URL) == text
    assert message.get_content(MentionStyle.REPLACE_WITH_URL) == text


def test_get_content_append_url_renders_each_mention() -> None:
    """
    `MentionStyle.APPEND_URL` keeps the username and adds the profile URL
    in parentheses for each mention.
    """

    message = Message(
        id="1",
        message="Hi @alice.bsky.social and @bob.bsky.social!",
        source_connection="test",
        metadata=MessageMetadata(
            mentions=[
                MessageMention(
                    url="https://bsky.app/profile/did:plc:alice",
                    username="@alice.bsky.social",
                ),
                MessageMention(
                    url="https://bsky.app/profile/did:plc:bob",
                    username="@bob.bsky.social",
                ),
            ],
        ),
    )

    assert message.get_content(MentionStyle.APPEND_URL) == (
        "Hi @alice.bsky.social (https://bsky.app/profile/did:plc:alice) "
        "and @bob.bsky.social (https://bsky.app/profile/did:plc:bob)!"
    )


def test_get_content_replace_with_url_swaps_handle() -> None:
    """
    `MentionStyle.REPLACE_WITH_URL` swaps the username text for the URL.
    """

    message = Message(
        id="1",
        message="Hi @alice.bsky.social!",
        source_connection="test",
        metadata=MessageMetadata(
            mentions=[
                MessageMention(
                    url="https://bsky.app/profile/did:plc:alice",
                    username="@alice.bsky.social",
                ),
            ],
        ),
    )

    assert (
        message.get_content(MentionStyle.REPLACE_WITH_URL)
        == "Hi https://bsky.app/profile/did:plc:alice!"
    )


def test_get_content_supports_markdown_link_style() -> None:
    """`MentionStyle.MARKDOWN_LINK` renders a markdown link per mention."""

    message = Message(
        id="1",
        message="Hi @alice.bsky.social!",
        source_connection="test",
        metadata=MessageMetadata(
            mentions=[
                MessageMention(
                    url="https://bsky.app/profile/did:plc:alice",
                    username="@alice.bsky.social",
                ),
            ],
        ),
    )

    assert (
        message.get_content(MentionStyle.MARKDOWN_LINK)
        == "Hi [@alice.bsky.social](https://bsky.app/profile/did:plc:alice)!"
    )


def test_get_content_supports_html_link_style() -> None:
    """`MentionStyle.HTML_LINK` renders an HTML link per mention."""

    message = Message(
        id="1",
        message="Hi @alice.bsky.social!",
        source_connection="test",
        metadata=MessageMetadata(
            mentions=[
                MessageMention(
                    url="https://bsky.app/profile/did:plc:alice",
                    username="@alice.bsky.social",
                ),
            ],
        ),
    )

    assert (
        message.get_content(MentionStyle.HTML_LINK)
        == 'Hi <a href="https://bsky.app/profile/did:plc:alice">'
        "@alice.bsky.social</a>!"
    )


def test_get_content_skips_handles_not_in_text() -> None:
    """
    A mention whose username text is missing from the body is skipped silently.
    """

    message = Message(
        id="1",
        message="Hello, world!",
        source_connection="test",
        metadata=MessageMetadata(
            mentions=[
                MessageMention(
                    url="https://bsky.app/profile/did:plc:ghost",
                    username="@ghost.bsky.social",
                ),
            ],
        ),
    )

    assert message.get_content(MentionStyle.APPEND_URL) == "Hello, world!"
    assert message.get_content(MentionStyle.REPLACE_WITH_URL) == "Hello, world!"
