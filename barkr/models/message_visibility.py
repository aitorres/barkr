"""
Module to implement generic enums and models to represent
a message's visibility.
"""

from enum import Enum


class MessageVisibility(Enum):
    """
    Represents the visibility of a message.
    """

    PUBLIC = 0
    UNLISTED = 1
    PRIVATE = 2
    DIRECT = 3

    @staticmethod
    def from_mastodon_visibility(visibility: str) -> "MessageVisibility":
        """
        Convert a Mastodon visibility string to a MessageVisibility enum.

        :param visibility: The visibility string from Mastodon
        :return: The corresponding MessageVisibility enum
        """
        if visibility == "public":
            return MessageVisibility.PUBLIC

        if visibility == "unlisted":
            return MessageVisibility.UNLISTED

        if visibility == "private":
            return MessageVisibility.PRIVATE

        if visibility == "direct":
            return MessageVisibility.DIRECT

        raise ValueError(f"Unknown Mastodon visibility: {visibility}")

    def to_mastodon_visibility(self) -> str:
        """
        Convert a MessageVisibility enum to a Mastodon visibility string.

        :return: The corresponding visibility string for Mastodon
        """

        if self == MessageVisibility.UNLISTED:
            return "unlisted"

        if self == MessageVisibility.PRIVATE:
            return "private"

        if self == MessageVisibility.DIRECT:
            return "direct"

        return "public"
