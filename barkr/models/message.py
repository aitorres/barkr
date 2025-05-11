"""
Module to implement a generic, wrapper model for messages.

A message is a generic object that can be posted to a social media network
OR retrieved from a social media network, with an ID and a message body, as
well as (potentially) other metadata that each connection can decide
whether or not to take into account.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from barkr.models.media import Media
from barkr.models.message_type import MessageType


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


@dataclass(frozen=True)
class Message:
    """
    A generic message object with an ID and a message body,
    as well as (potentially) other metadata that each connection
    can decide whether or not to take into account.
    """

    # Main attributes
    id: str
    message: str

    # Messages can optionally have media attached to them, which are
    # stored in a list per their byte representation and MIME type.
    media: list[Media] = field(default_factory=list)

    # Optional metadata
    language: Optional[str] = None
    label: Optional[str] = None
    visibility: MessageVisibility = MessageVisibility.PUBLIC

    def has_content(self, supported_message_type: MessageType) -> bool:
        """
        Check if the message has content and therefore can be published.

        At this point, the only check is whether the message is empty or not.
        We also check if the message is direct or private, as these messages
        might not be aimed for public posting.

        In the future, as Messages grow in complexity, this method may be
        extended to check for other conditions (e.g. accounting for
        a message with no text but with an image).

        :return: True if the message has content, False otherwise
        """

        # If the message is private or direct, we don't want to post it
        if self.visibility in (MessageVisibility.PRIVATE, MessageVisibility.DIRECT):
            return False

        has_text = bool(self.message.strip())

        # If we support media, we can post a message with no text
        # as long as it has media
        if supported_message_type == MessageType.TEXT_MEDIA:
            valid_media = [m for m in self.media if m.is_valid()]
            has_media = len(valid_media) > 0

            # If we have media, we can post the message
            return has_text or has_media

        # By default, we only support text messages
        return has_text
