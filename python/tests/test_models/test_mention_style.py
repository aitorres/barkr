"""
Module to implement unit tests for the MentionStyle enum helper.
"""

from barkr.models.mention_style import MentionStyle
from barkr.models.message_mention import MessageMention


def test_replace_mentions_supports_all_styles() -> None:
    """The helper should rewrite mentions for every supported style."""

    text = "Hi @alice.bsky.social and @bob.bsky.social!"
    mentions = [
        MessageMention(
            url="https://bsky.app/profile/did:plc:alice",
            username="@alice.bsky.social",
        ),
        MessageMention(
            url="https://bsky.app/profile/did:plc:bob",
            username="@bob.bsky.social",
        ),
    ]

    assert MentionStyle.replace_mentions(text, mentions, MentionStyle.PLAIN) == text
    assert MentionStyle.replace_mentions(text, mentions, MentionStyle.APPEND_URL) == (
        "Hi @alice.bsky.social (https://bsky.app/profile/did:plc:alice) "
        "and @bob.bsky.social (https://bsky.app/profile/did:plc:bob)!"
    )
    assert MentionStyle.replace_mentions(
        text, mentions, MentionStyle.REPLACE_WITH_URL
    ) == (
        "Hi https://bsky.app/profile/did:plc:alice and "
        "https://bsky.app/profile/did:plc:bob!"
    )
    assert MentionStyle.replace_mentions(
        text, mentions, MentionStyle.MARKDOWN_LINK
    ) == (
        "Hi [@alice.bsky.social](https://bsky.app/profile/did:plc:alice) "
        "and [@bob.bsky.social](https://bsky.app/profile/did:plc:bob)!"
    )
    assert MentionStyle.replace_mentions(text, mentions, MentionStyle.HTML_LINK) == (
        'Hi <a href="https://bsky.app/profile/did:plc:alice">'
        "@alice.bsky.social</a> and "
        '<a href="https://bsky.app/profile/did:plc:bob">'
        "@bob.bsky.social</a>!"
    )


def test_replace_mentions_short_circuits_without_mentions() -> None:
    """The helper must leave the text untouched when mentions are absent."""

    text = "Hello, world!"

    assert MentionStyle.replace_mentions(text, None, MentionStyle.APPEND_URL) == text
    assert MentionStyle.replace_mentions(text, [], MentionStyle.HTML_LINK) == text


def test_replace_mentions_handles_repeated_same_username() -> None:
    """Repeated usernames should be rewritten one occurrence at a time."""

    text = "Hi @bob I love @bob how're you doing @bob"
    mentions = [
        MessageMention(url="https://example.com/u/bob-1", username="@bob"),
        MessageMention(url="https://example.com/u/bob-2", username="@bob"),
        MessageMention(url="https://example.com/u/bob-3", username="@bob"),
    ]

    assert MentionStyle.replace_mentions(text, mentions, MentionStyle.APPEND_URL) == (
        "Hi @bob (https://example.com/u/bob-1) "
        "I love @bob (https://example.com/u/bob-2) "
        "how're you doing @bob (https://example.com/u/bob-3)"
    )

    assert MentionStyle.replace_mentions(
        text, mentions, MentionStyle.REPLACE_WITH_URL
    ) == (
        "Hi https://example.com/u/bob-1 "
        "I love https://example.com/u/bob-2 "
        "how're you doing https://example.com/u/bob-3"
    )
