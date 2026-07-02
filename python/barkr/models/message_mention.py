"""
Module to implement a generic, wrapper model for a user mention
extracted from a source post (e.g. a Bluesky mention facet).
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MessageMention:
    """
    A user mention extracted from a message's source post: includes
    the literal username text from the message body, and the profile
    URL of the mentioned user on the source service.
    """

    url: str
    username: str
