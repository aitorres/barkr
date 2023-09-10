"""
Module to implement the base class and enums for custom
connections to social media networks, chat services, etc.
"""

import logging
from enum import Enum

from barkr.models.message import Message

logger = logging.getLogger()


class ConnectionMode(Enum):
    """
    Enum to represent connection modes
    """

    READ = 1
    WRITE = 2


class Connection:
    """
    Base class to represent a connection to a social media network,
    chat service, etc.

    Subclasses should implement the _fetch and _post methods, which will
    be called depending on the modes each connection is set up with.

    The base clase already supports a validation to avoid duplicate posting
    of messages already posted by one connection on subsequent fetches.
    """

    def __init__(self, name: str, modes: list[ConnectionMode]) -> None:
        """
        Initializes the connection with a name and a list of modes

        :param name: The name of the connection
        :param modes: A list of modes for the connection
        """

        self.name: str = name
        self.modes: list[ConnectionMode] = modes
        self.posted_message_ids: set[str] = set()

    def read(self) -> list[Message]:
        """
        Read and return new messages from this connection

        :return: A list of new messages
        """

        if ConnectionMode.READ not in self.modes:
            return []

        messages: list[Message] = self._fetch()

        filtered_messages: list[Message] = []
        for message in messages:
            if (status_id := message.id) not in self.posted_message_ids:
                filtered_messages.append(message)
            else:
                logger.debug("Status %s already posted, skipping.", status_id)
                self.posted_message_ids.remove(status_id)

        return filtered_messages

    def write(self, messages: list[Message]) -> None:
        """
        Write messages to this connection

        :param messages: A list of messages to be posted
        """

        if ConnectionMode.WRITE not in self.modes:
            return

        posted_ids: list[str] = self._post(messages)
        self.posted_message_ids.update(posted_ids)

    def _fetch(self) -> list[Message]:
        """
        Fetch messages from this connection and returns a list of pairs
        containing (id, message)

        :return: A list of pairs containing (id, message)
        """

        raise NotImplementedError(f"Fetch not implemented for connection {self.name}")

    def _post(self, messages: list[Message]) -> list[str]:
        """
        Post messages to this connection and returns a list of message IDs

        :param messages: A list of messages to be posted
        :return: A list of message IDs
        """

        raise NotImplementedError(f"Post not implemented for connection {self.name}")
