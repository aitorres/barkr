"""
Module to implement unit tests for the MessageAllowedReplies enum.
"""

import pytest
from atproto_client.models.app.bsky.feed.threadgate import (  # type: ignore
    FollowerRule,
    FollowingRule,
    MentionRule,
)

from barkr.models import MessageAllowedReplies


def test_message_allowed_replies_to_bluesky_threadgate() -> None:
    """
    Test that we can convert MessageAllowedReplies to a Bluesky thread gate record
    managing rules for who can reply to a message as expected.
    """

    post_record_uri = "at://did:example:12345/app.bsky.feed.post/67890"
    current_time = "2025-08-04T12:00:00Z"

    # Test with no restrictions
    assert (
        MessageAllowedReplies.to_bluesky_threadgate(post_record_uri, [], current_time)
        is None
    )

    # Test with only EVERYONE
    assert (
        MessageAllowedReplies.to_bluesky_threadgate(
            post_record_uri, [MessageAllowedReplies.EVERYONE], current_time
        )
        is None
    )

    # Test with NO_ONE
    record = MessageAllowedReplies.to_bluesky_threadgate(
        post_record_uri, [MessageAllowedReplies.NO_ONE], current_time
    )
    assert record is not None
    assert record.allow == []

    # NO_ONE should always absorb other rules
    record = MessageAllowedReplies.to_bluesky_threadgate(
        post_record_uri,
        [MessageAllowedReplies.NO_ONE, MessageAllowedReplies.FOLLOWERS],
        current_time,
    )
    assert record is not None
    assert record.allow == []

    # Test with multiple rules including EVERYONE (should raise an error)
    with pytest.raises(ValueError):
        MessageAllowedReplies.to_bluesky_threadgate(
            post_record_uri,
            [MessageAllowedReplies.EVERYONE, MessageAllowedReplies.FOLLOWERS],
            current_time,
        )

    # Test with a single rule
    record = MessageAllowedReplies.to_bluesky_threadgate(
        post_record_uri,
        [MessageAllowedReplies.FOLLOWERS],
        current_time,
    )
    assert record is not None
    assert len(record.allow) == 1
    assert isinstance(record.allow[0], FollowerRule)

    # Test with multiple rules
    record = MessageAllowedReplies.to_bluesky_threadgate(
        post_record_uri,
        [
            MessageAllowedReplies.FOLLOWERS,
            MessageAllowedReplies.FOLLOWING,
            MessageAllowedReplies.MENTIONED_USERS,
        ],
        current_time,
    )
    assert record is not None
    assert len(record.allow) == 3
    assert isinstance(record.allow[0], FollowerRule)
    assert isinstance(record.allow[1], FollowingRule)
    assert isinstance(record.allow[2], MentionRule)
