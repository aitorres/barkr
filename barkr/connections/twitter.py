"""
Module to implement a custom connection class for Twitter (X),
supporting writing tweets from the authenticated user via their API keys.

This module uses the Tweepy library to interact with the Twitter API.
"""

import logging
from typing import Final

from tweepy import Client

from barkr.connections.base import Connection, ConnectionMode
from barkr.models import Message

logger = logging.getLogger()


TWITTER_MAX_LENGTH: Final[int] = 280


class TwitterConnection(Connection):
    """
    Custom connection class for Twitter, supporting writing tweets
    from the authenticated user via their API keys.
    """

    client: Client

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        name: str,
        modes: list[ConnectionMode],
        consumer_key: str,
        consumer_secret: str,
        access_token: str,
        access_token_secret: str,
        bearer_token: str,
    ) -> None:
        """
        Initializes the connection with a name and a list of modes
        as well as the Twitter API v1 and v2 credentials.

        Authenticates the tweepy client with the provided credentials.

        NOTE: only the write mode is supported. Attempting to use read
        mode will raise a NotImplementedError.

        NOTE: we are only using v2 of the Twitter API, some of the API keys
        might not be needed.

        :param name: The name of the connection
        :param modes: A list of modes for the connection
        :param consumer_key: The consumer key for the Twitter API
        :param consumer_secret: The consumer secret for the Twitter API
        :param access_token: The access token for the authenticated user
        :param access_token_secret: The access token secret for the authenticated user
        :param bearer_token: The bearer token for the Twitter API v2
        """
        super().__init__(name, modes)

        logger.info("Initializing Twitter (%s) connection", self.name)
        if self.modes != [ConnectionMode.WRITE]:
            raise NotImplementedError("TwitterConnection only supports write mode.")

        self.client = Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            bearer_token=bearer_token,
        )
        logger.info("Twitter (%s) connection initialized!", self.name)

    def _post(self, messages: list[Message]) -> list[str]:
        """
        Post a list of messages as tweets from the authenticated user.

        :param messages: A list of messages to post as tweets
        :return: A list of message IDs
        """

        posted_message_ids: list[str] = []

        for message in messages:
            if len(message.message) > TWITTER_MAX_LENGTH:
                logger.warning(
                    "Message exceeds Twitter's max length (%s characters), skipping: %s",
                    TWITTER_MAX_LENGTH,
                    message.message,
                )
                continue

            posted_tweet_response = self.client.create_tweet(text=message.message)
            posted_tweet_id = posted_tweet_response.data["id"]
            posted_message_ids.append(posted_tweet_id)
            logger.info("Tweeted message: %s", message.message)

        return posted_message_ids
