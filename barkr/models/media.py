"""
Module to implement a generic representation of media objects
that can be posted or retrieved as part of messages
"""

from dataclasses import dataclass
from typing import Final

SUPPORTED_MIME_TYPES: Final[set[str]] = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "video/mp4",
    "video/quicktime",
}


@dataclass(frozen=True)
class Media:
    """
    A generic media object with a MIME type and the content
    in bytes.

    Can be retrieved as part of a message or posted
    to a social media network.
    """

    # Required attributes to represent a media object
    mime_type: str
    content: bytes

    # Optional metadata
    alt_text: str = ""

    def is_valid(self) -> bool:
        """
        Check if the media object is valid and can be
        posted to a social media network or otherwise
        handled.

        For a media object to be valid, it must have
        a non-empty content and a valid MIME type.
        """

        has_content = len(self.content) > 0
        has_mime_type = self.mime_type.strip()

        if not has_content or not has_mime_type:
            return False

        return self.mime_type in SUPPORTED_MIME_TYPES
