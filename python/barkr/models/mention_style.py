"""
Module to implement an enum representing how mentions should be
rendered when serializing a message's body for a given publisher.
"""

from enum import Enum
from typing import Optional

from barkr.models.message_mention import MessageMention


class MentionStyle(Enum):
    """
    Represents how mentions should be rendered when serializing
    a message's body for a given publisher.
    """

    # Leave the message body untouched
    PLAIN = 0

    # Keep the original handle text and append the profile URL in parentheses
    APPEND_URL = 1

    # Replace the original handle text with the profile URL
    REPLACE_WITH_URL = 2

    # Render mentions as markdown links with the username as link text
    # and the profile URL as the link target
    MARKDOWN_LINK = 3

    # Render mentions as HTML links with the username as link text and the
    # profile URL as the href target
    HTML_LINK = 4

    @staticmethod
    def replace_mentions(
        text: str,
        mentions: Optional[list[MessageMention]],
        mention_style: Optional["MentionStyle"] = None,
    ) -> str:
        """
        Replace mentions in a text body according to a render style.

        :param text: The source text to rewrite
        :param mentions: The mention metadata extracted from the source post
        :param mention_style: The style to use when rendering mentions
        :return: The rewritten text
        """

        if mention_style is None:
            mention_style = MentionStyle.PLAIN

        if mention_style == MentionStyle.PLAIN or not mentions:
            return text

        content_parts: list[str] = []
        cursor = 0
        for mention in mentions:
            start = text.find(mention.username, cursor)
            if start == -1:
                continue

            content_parts.append(text[cursor:start])
            if mention_style == MentionStyle.APPEND_URL:
                replacement = f"{mention.username} ({mention.url})"
            elif mention_style == MentionStyle.REPLACE_WITH_URL:
                replacement = mention.url
            elif mention_style == MentionStyle.MARKDOWN_LINK:
                replacement = f"[{mention.username}]({mention.url})"
            elif mention_style == MentionStyle.HTML_LINK:
                replacement = f'<a href="{mention.url}">{mention.username}</a>'
            else:
                raise ValueError(f"Unsupported mention style: {mention_style}")

            content_parts.append(replacement)
            cursor = start + len(mention.username)

        content_parts.append(text[cursor:])
        return "".join(content_parts)
