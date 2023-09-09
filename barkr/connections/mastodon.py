"""
Module to implement a custom connection class for Mastodon instances,
supporting reading and writing statuses from the authenticated user
via their access token.
"""

import logging
from typing import Any

from mastodon import Mastodon  # type: ignore

from barkr.connections.base import Connection, ConnectionMode

logger = logging.getLogger()


class MastodonConnection(Connection):
    """
    Custom connection class for Mastodon instances,
    supporting reading and writing statuses from the authenticated user.
    """

    service: Mastodon
    account_id: str
    min_id: str

    def __init__(
        self,
        name: str,
        modes: list[ConnectionMode],
        access_token: str,
        instance_url: str,
    ) -> None:
        """
        Initializes the connection with a name and a list of modes
        as well as the access token and instance URL.

        Validates the access token and instance URL by attempting to
        verify the credentials of the authenticated user and retrieve
        the account ID.

        :param name: The name of the connection
        :param modes: A list of modes for the connection
        :param access_token: The access token for the authenticated user
        :param instance_url: The URL of the Mastodon instance
        """
        super().__init__(name, modes)

        logger.debug(
            "Initializing Mastodon (%s) connection to instance %s",
            self.name,
            instance_url,
        )
        self.service = Mastodon(
            access_token=access_token,
            api_base_url=instance_url,
        )
        self.account_id = self.service.account_verify_credentials()["id"]
        logger.info(
            "Mastodon (%s) connection initialized! (Account ID: %s)",
            self.name,
            self.account_id,
        )

        current_statuses = self.service.account_statuses(
            self.account_id, exclude_reblogs=True, exclude_replies=True
        )
        if current_statuses:
            self.min_id = current_statuses[0]["id"]
            logger.debug("Mastodon (%s) initial min_id: %s", self.name, self.min_id)
        else:
            self.min_id = ""
            logger.debug("Mastodon (%s) initial min_id not set.", self.name)

    def _fetch(self) -> list[str]:
        """
        Fetch messages from this connection
        """

        statuses: list[dict[str, Any]] = self.service.account_statuses(
            self.account_id,
            exclude_reblogs=True,
            exclude_replies=True,
            min_id=self.min_id,
        )

        if statuses:
            logger.info(
                "Fetched %s new statuses from Mastodon (%s)", len(statuses), self.name
            )
            self.min_id = statuses[-1]["id"]
        else:
            logger.debug("No new statuses fetched from Mastodon (%s)", self.name)

        return [status["content"] for status in statuses]

    def _post(self, messages: list[str]) -> None:
        """
        Post messages from a list to the Mastodon instance

        :param messages: A list of messages to be posted
        """

        for message in messages:
            self.service.status_post(message)
            logger.info("Posted status to Mastodon (%s): %s", self.name, message)
