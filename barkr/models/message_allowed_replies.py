"""
Module to implement a generic enum to represent
who can reply to a message.
"""

from enum import Enum
from typing import Optional, Union

from atproto_client.models import AppBskyFeedThreadgate  # type: ignore
from atproto_client.models.app.bsky.feed.threadgate import (  # type: ignore
    FollowerRule,
    FollowingRule,
    ListRule,
    MentionRule,
)


class MessageAllowedReplies(Enum):
    """
    Represents who can reply to a message,
    for example: everyone, or just followers...
    """

    EVERYONE = 0
    FOLLOWERS = 1
    FOLLOWING = 2
    MENTIONED_USERS = 3
    NO_ONE = 4

    @staticmethod
    def to_bluesky_threadgate(
        post_record_uri: str,
        allowed_replies: list["MessageAllowedReplies"],
        current_time: str,
    ) -> Optional[AppBskyFeedThreadgate.Record]:
        """
        Convert a list of MessageAllowedReplies to a Bluesky thread gate record
        that can be used to limit who can reply to a post.

        :param allowed_replies: List of MessageAllowedReplies
        :return: AppBskyFeedThreadgate.Record with the appropriate reply settings,
                 or None if no restrictions are set
        """

        # If no rules are provided, return None to signal no restrictions
        if not allowed_replies:
            return None

        # If the only rule is EVERYONE, we can return None
        if allowed_replies == [MessageAllowedReplies.EVERYONE]:
            return None

        # If EVERYONE is used with other rules, we raise an error
        if MessageAllowedReplies.EVERYONE in allowed_replies:
            raise ValueError("Cannot use EVERYONE with other allowed replies rules.")

        # If NO_ONE is used, we return an empty thread gate record
        # to indicate no replies are allowed
        if MessageAllowedReplies.NO_ONE in allowed_replies:
            return AppBskyFeedThreadgate.Record(
                post=post_record_uri,
                allow=[],
                created_at=current_time,
            )

        # Otherwise, we build the thread gate record with the allowed replies
        allow: list[Union[MentionRule, FollowerRule, FollowingRule, ListRule]] = []

        if MessageAllowedReplies.FOLLOWERS in allowed_replies:
            allow.append(AppBskyFeedThreadgate.FollowerRule())

        if MessageAllowedReplies.FOLLOWING in allowed_replies:
            allow.append(AppBskyFeedThreadgate.FollowingRule())

        if MessageAllowedReplies.MENTIONED_USERS in allowed_replies:
            allow.append(AppBskyFeedThreadgate.MentionRule())

        return AppBskyFeedThreadgate.Record(
            post=post_record_uri,
            allow=allow,
            created_at=current_time,
        )
