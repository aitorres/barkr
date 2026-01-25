"""
Module to implement a generic, wrapper model for message metadata.

Message metadata contains optional information about a message
such as language, visibility, and allowed replies. This data
is separated from the core message to keep the Message class
focused on the essential message content.
"""

from dataclasses import dataclass
from typing import Optional

from barkr.models.message_allowed_replies import MessageAllowedReplies
from barkr.models.message_visibility import MessageVisibility


@dataclass(frozen=True)
class MessageMetadata:
    """
    A container for optional message metadata such as
    language, label, visibility, and allowed replies.
    """

    language: Optional[str] = None
    label: Optional[str] = None
    visibility: MessageVisibility = MessageVisibility.PUBLIC
    allowed_replies: Optional[list[MessageAllowedReplies]] = None
