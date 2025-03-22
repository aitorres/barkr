"""
Module to implement a custom connection class for RSS feeds,
supporting reading messages from a given feed.
"""

import logging
from time import struct_time
from typing import Callable, Optional

import feedparser

from barkr.connections.base import Connection, ConnectionMode
from barkr.models import Message

logger = logging.getLogger()


def default_feed_message_callback(url: str, title: str) -> str:
    """
    Given the URL and title of an RSS feed entry,
    returns a string that represents the message to be sent.

    The content of the message is formatted as follows:
        <title>: <url>

    :param url: The URL of the feed entry`
    :param title: The title of the feed entry
    :return: a string representation of the feed entry as a message
    """

    return f"{title}: {url}"


class RSSConnection(Connection):
    """
    Custom connection class for RSS feeds,
    supporting reading messages from a given feed.
    """

    feed_url: str
    feed_message_callback: Callable[[str, str], str]
    feed_min_date: Optional[struct_time] = None

    def __init__(
        self,
        name: str,
        modes: list[ConnectionMode],
        feed_url: str,
        feed_message_callback: Callable[
            [str, str], str
        ] = default_feed_message_callback,
    ) -> None:
        """
        Initializes the connection with a name and a list of modes, as well as the
        RSS feed URL.

        NOTE: only the read mode is supported. Attempting to use write mode
        will raise a NotImplementedError.

        :param name: The name of the connection
        :param modes: A list of modes for the connection
        :param feed_url: The URL of the RSS feed
        """
        super().__init__(name, modes)

        logger.info("Initializing RSS (%s) connection", self.name)
        if self.modes != [ConnectionMode.READ]:
            raise NotImplementedError("RSSConnection only supports read mode.")

        # Storing parameters for later use
        self.feed_url = feed_url
        self.feed_message_callback = feed_message_callback

        # Getting most recent post date
        try:
            feed = feedparser.parse(self.feed_url)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error on initial RSS feed fetch : %s", e)
        else:
            if feed.entries:
                # Set the initial min_date to the most recent post's published date
                self.feed_min_date = feed.entries[0].published_parsed
                logger.info(
                    "RSS (%s) initial min_date: %s", self.name, self.feed_min_date
                )
            else:
                logger.info(
                    "RSS (%s) initial min_date not set "
                    "(no entries found on initial fetch).",
                    self.name,
                )

        logger.info("RSS (%s) connection initialized successfully", self.name)

    def _fetch(self) -> list[Message]:
        """
        Fetch messages from the RSS feed.

        :return: A list of messages from the feed
        """
        logger.info("Fetching messages from RSS (%s) connection", self.name)

        try:
            feed = feedparser.parse(self.feed_url)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error fetching RSS feed: %s", e)
            return []

        logger.info("Fetched RSS feed successfully!")

        messages = []
        for entry in feed.entries:
            if self.feed_min_date and entry.published_parsed <= self.feed_min_date:
                continue

            message = Message(
                id=entry.link,
                message=self.feed_message_callback(entry.link, entry.title),
            )
            messages.append(message)

        # Updated min_date to the most recent post's published date
        if feed.entries:
            self.feed_min_date = feed.entries[0].published_parsed

        logger.info(
            "Fetched %d messages from RSS (%s) connection", len(messages), self.name
        )
        return messages
