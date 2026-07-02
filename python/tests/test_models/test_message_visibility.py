"""
Module to implement unit tests for the MessageVisibility class.
"""

import pytest

from barkr.models.message import MessageVisibility


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
