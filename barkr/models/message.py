"""
Module to implement a generic, wrapper model for messages.

A message is a generic object that can be posted to a social media network
OR retrieved from a social media network, with an ID and a message body, as
well as (potentially) other metadata that each connection can decide
whether or not to take into account.
"""

from dataclasses import dataclass
from typing import Optional


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

    # Optional metadata
    language: Optional[str] = None

    def has_content(self) -> bool:
        """
        Check if the message has content and therefore can be published.

        At this point, the only check is whether the message is empty or not.
        In the future, as Messages grow in complexity, this method may be
        extended to check for other conditions (e.g. accounting for
        a message with no text but with an image).

        :return: True if the message has content, False otherwise
        """

        return bool(self.message)
