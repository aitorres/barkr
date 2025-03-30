"""
Module to implement a custom connection class for ActivityBot,
an ActivityPub bot for Mastodon.

Supports writing statuses to Mastodon from the bot via
their API url and password.

ref: https://gitlab.com/edent/activity-bot
"""

import logging

import requests

from barkr.connections.base import Connection, ConnectionMode
from barkr.models import Message
from barkr.utils import REQUESTS_EMBED_GET_TIMEOUT, REQUESTS_HEADERS

logger = logging.getLogger()


class MastodonActivityBotConnection(Connection):
    """
    Custom connection class for ActivityBot, an ActivityPub bot for Mastodon.

    Supports writing statuses to Mastodon from the bot via
    their API url and password.
    """

    password: str
    api_url: str

    def __init__(
        self, name: str, modes: list[ConnectionMode], api_url: str, password: str
    ) -> None:
        """
        Initializes the connection with a name, API URL, and password.

        :param name: The name of the connection
        :param modes: A list of modes for the connection
        :param api_url: The API URL for the ActivityBot send action
        :param password: The password for the ActivityBot
        """
        super().__init__(name, modes)

        logger.info("Initializing MastodonActivityBot (%s) connection", self.name)
        if self.modes != [ConnectionMode.WRITE]:
            raise NotImplementedError(
                "MastodonActivityBotConnection only supports write mode."
            )

        self.api_url = api_url
        self.password = password

        logger.info(
            "MastodonActivityBot (%s) connection initialized! (API URL: %s)",
            self.name,
            self.api_url,
        )

    def _post(self, messages: list[Message]) -> list[str]:
        """
        Posts the given messages to ActivityPub via
        the ActivityBot send action.

        :param messages: The list of messages to post
        :return: A list of message IDs (empty for ActivityBot)
        """

        for message in messages:
            logger.info(
                "Posting message to ActivityBot (%s): %s", self.name, message.message
            )
            response = requests.post(
                self.api_url,
                data={"password": self.password, "content": message.message},
                headers=REQUESTS_HEADERS,
                timeout=REQUESTS_EMBED_GET_TIMEOUT,
            )

            if response.status_code != 200:
                logger.error(
                    "Failed to post message to ActivityBot (%s): %s",
                    self.name,
                    response.text,
                )

        return []
