"""
Module to implement a custom connection class for Bluesky accounts,
supporting reading and writing statuses from the authenticated user
via their handle and password.
"""

import logging
from typing import Optional

from atproto import Client

from barkr.connections.base import Connection, ConnectionMode
from barkr.models.message import Message

logger = logging.getLogger()


class BlueskyConnection(Connection):
    """
    Custom connection class for Bluesky accounts,
    supporting reading and writing statuses from the authenticated user.

    Requires handle and an app password for authentication.
    """

    def __init__(
        self, name: str, modes: list[ConnectionMode], handle: str, password: str
    ) -> None:
        """
        Initializes the connection with a name and a list of modes
        and sets up the initial connection between the client and Bluesky
        for the given user.

        :param name: The name of the connection
        :param modes: A list of modes for the connection
        :param handle: The handle of the authenticated user
        :param password: The app password of the authenticated user
        """

        super().__init__(name, modes)

        logger.debug(
            "Initializing Bluesky (%s) connection for user %s",
            self.name,
            handle,
        )

        self.service = Client()
        self.service.login(handle, password)
        self.handle: str = handle

        logger.info(
            "Bluesky (%s) connection initialized! (User handle: %s)",
            self.name,
            self.handle,
        )

        user_feed = self.service.app.bsky.feed.get_author_feed({"actor": handle}).feed
        if user_feed:
            self.min_id: Optional[str] = user_feed[0].post.indexed_at
            logger.debug("Bluesky (%s) initial min_id: %s", self.name, self.min_id)
        else:
            self.min_id = None
            logger.debug("Bluesky (%s) initial min_id not set.", self.name)

    def _fetch(self) -> list[Message]:
        """
        Fetches messages from the authenticated user's account.

        :return: A list of messages
        """

        messages: list[Message] = []

        user_feed = self.service.app.bsky.feed.get_author_feed(
            {"actor": self.handle}
        ).feed
        if user_feed:
            for feed_view in user_feed:
                post = feed_view.post

                if post.indexed_at > self.min_id:
                    messages.append(
                        Message(id=post.indexed_at, message=post.record.text)
                    )

        if messages:
            self.min_id = messages[0].id
            logger.info("Bluesky (%s) has %s new messages.", self.name, len(user_feed))
        else:
            logger.debug("Bluesky (%s) has no new messages.", self.name)

        return messages

    def _post(self, messages: list[Message]) -> list[str]:
        """
        Posts the given messages to the authenticated user's account.

        :param messages: The messages to post
        :return: A list of IDs of the posted messages
        """

        posted_message_ids: list[str] = []

        for message in messages:
            record = self.service.send_post(text=message.message)
            posted_message_ids.append(record.indexed_at)
            logger.info(
                "Posted message %s to Bluesky (%s) connection (ID: %s, Indexed At: %s)",
                message.message,
                self.name,
                record.cid,
                record.indexed_at,
            )

        return posted_message_ids
