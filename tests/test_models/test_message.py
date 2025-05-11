"""
Module to implement unit tests for the Message class.
"""

import pytest

from barkr.models.media import Media
from barkr.models.message import Message, MessageVisibility
from barkr.models.message_type import MessageType


def test_message() -> None:
    """
    Test that the Message class is initialized correctly
    """

    message_1 = Message(
        id="12345", message="Hello, world!", language="en", label="greeting"
    )

    assert message_1.id == "12345"
    assert message_1.message == "Hello, world!"
    assert message_1.language == "en"
    assert message_1.label == "greeting"
    assert message_1.visibility == MessageVisibility.PUBLIC

    message_2 = Message(
        id="67890",
        message="Bonjour le monde!",
    )
    assert message_2.id == "67890"
    assert message_2.message == "Bonjour le monde!"
    assert message_2.language is None
    assert message_2.label is None
    assert message_2.visibility == MessageVisibility.PUBLIC

    message_3 = Message(
        id="abcde",
        message="Hola, mundo!",
        visibility=MessageVisibility.PRIVATE,
    )
    assert message_3.id == "abcde"
    assert message_3.message == "Hola, mundo!"
    assert message_3.language is None
    assert message_3.label is None
    assert message_3.visibility == MessageVisibility.PRIVATE


def test_message_has_content() -> None:
    """
    Test that the has_content method appropriately
    tells if the Message contains content or not.
    """

    # Base case: check is done for a text-only connection
    assert Message(id="12345", message="Hello, world!").has_content(
        MessageType.TEXT_ONLY
    )
    assert not Message(id="12345", message="").has_content(MessageType.TEXT_ONLY)
    assert not Message(id="12345", message="   ").has_content(MessageType.TEXT_ONLY)
    assert not Message(id="12345", message="\n").has_content(MessageType.TEXT_ONLY)
    assert Message(id="12345", message="Hello, world!", label="greeting").has_content(
        MessageType.TEXT_ONLY
    )

    # Check for a message with a media object
    media_list = [
        Media(mime_type="image/jpeg", content=b"image data"),
        Media(mime_type="video/mp4", content=b"video data"),
    ]
    assert Message(id="12345", message="Hello, world!", media=media_list).has_content(
        MessageType.TEXT_MEDIA
    )
    assert Message(id="12345", message="", media=media_list).has_content(
        MessageType.TEXT_MEDIA
    )
    assert Message(id="12345", message="   ", media=media_list).has_content(
        MessageType.TEXT_MEDIA
    )
    assert Message(id="12345", message="\n", media=media_list).has_content(
        MessageType.TEXT_MEDIA
    )

    invalid_media_list = [
        Media(mime_type="text/plain", content=b"invalid media"),
        Media(mime_type="application/json", content=b"invalid media"),
    ]
    assert Message(
        id="12345", message="Hello, world!", media=invalid_media_list
    ).has_content(MessageType.TEXT_MEDIA)
    assert not Message(id="12345", message="", media=invalid_media_list).has_content(
        MessageType.TEXT_MEDIA
    )
    assert not Message(id="12345", message="   ", media=invalid_media_list).has_content(
        MessageType.TEXT_MEDIA
    )

    empty_media_list: list[Media] = []
    assert Message(
        id="12345", message="Hello, world!", media=empty_media_list
    ).has_content(MessageType.TEXT_MEDIA)
    assert not Message(id="12345", message="", media=empty_media_list).has_content(
        MessageType.TEXT_MEDIA
    )
    assert not Message(id="12345", message="   ", media=empty_media_list).has_content(
        MessageType.TEXT_MEDIA
    )

    # We skip messages that have private or direct visibility,
    # even if they have content.
    assert not Message(
        id="12345",
        message="Hello, world!",
        visibility=MessageVisibility.PRIVATE,
    ).has_content(MessageType.TEXT_ONLY)
    assert not Message(
        id="12345",
        message="Hello, world!",
        visibility=MessageVisibility.DIRECT,
    ).has_content(MessageType.TEXT_ONLY)

    # Test with a message that has no content but is private
    assert not Message(
        id="12345",
        message="",
        visibility=MessageVisibility.PRIVATE,
    ).has_content(MessageType.TEXT_ONLY)


def test_message_visibility_from_mastodon() -> None:
    """
    Test that we can convert Mastodon visibility strings
    to MessageVisibility enums as expected.
    """

    assert (
        MessageVisibility.from_mastodon_visibility("public") == MessageVisibility.PUBLIC
    )
    assert (
        MessageVisibility.from_mastodon_visibility("unlisted")
        == MessageVisibility.UNLISTED
    )
    assert (
        MessageVisibility.from_mastodon_visibility("private")
        == MessageVisibility.PRIVATE
    )
    assert (
        MessageVisibility.from_mastodon_visibility("direct") == MessageVisibility.DIRECT
    )

    with pytest.raises(ValueError, match="Unknown Mastodon visibility: unknown"):
        MessageVisibility.from_mastodon_visibility("unknown")


def test_message_visibility_to_mastodon() -> None:
    """
    Test that we can convert MessageVisibility enums
    to Mastodon visibility strings as expected.
    """

    assert MessageVisibility.PUBLIC.to_mastodon_visibility() == "public"
    assert MessageVisibility.UNLISTED.to_mastodon_visibility() == "unlisted"
    assert MessageVisibility.PRIVATE.to_mastodon_visibility() == "private"
    assert MessageVisibility.DIRECT.to_mastodon_visibility() == "direct"
