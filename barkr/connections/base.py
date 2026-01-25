"""
Module to implement the base class and enums for custom
connections to social media networks, chat services, etc.
"""

import logging
from enum import Enum
from threading import Lock
from typing import Optional

from barkr.models import Message, MessageType

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

    name: str
    modes: list[ConnectionMode]
    posted_message_ids: set[str]
    supported_message_type: MessageType = MessageType.TEXT_ONLY

    def __init__(self, name: str, modes: list[ConnectionMode]) -> None:
        """
        Initializes the connection with a name and a list of modes

        :param name: The name of the connection
        :param modes: A list of modes for the connection
        """

        if not modes:
            raise ValueError("At least one mode must be provided for the connection.")

        if len(set(modes)) != len(modes):
            raise ValueError("Duplicate modes are not allowed for the connection.")

        self.name = name
        self.modes = modes
        self.posted_message_ids = set()

    def read(self) -> list[Message]:
        """
        Read and return new messages from this connection

        :return: A list of new messages
        """

        if ConnectionMode.READ not in self.modes:
            return []

        try:
            messages: list[Message] = self._fetch()
        except Exception as e:  # pylint: disable=broad-except
            if isinstance(e, NotImplementedError):
                raise

            logger.error(
                "Error fetching messages from connection %s: %s (%s)",
                self.name,
                str(e) or "(no error message)",
                type(e).__name__,
            )
            return []

        new_messages: list[Message] = []
        for message in messages:
            if (status_id := message.id) not in self.posted_message_ids:
                new_messages.append(message)
            else:
                logger.info("Status %s already posted, skipping.", status_id)

        return new_messages

    def write(self, messages: list[Message]) -> None:
        """
        Write messages to this connection

        :param messages: A list of messages to be posted
        """

        if ConnectionMode.WRITE not in self.modes:
            return

        # Discarding any empty messages
        messages_with_content = [
            message
            for message in messages
            if message.has_content(self.supported_message_type)
        ]

        if not messages_with_content:
            logger.warning(
                "All messages are empty (no content) for connection %s", self.name
            )
            return

        if len(messages_with_content) != len(messages):
            logger.warning(
                "Discarded %s empty messages for connection %s",
                len(messages) - len(messages_with_content),
                self.name,
            )

        posted_ids: list[str] = self._post(messages_with_content)
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


class ThreadAwareConnection(Connection):
    """
    Extended Connection class that supports reply-chain (thread) tracking
    across connections.

    This class maintains a shared mapping of message IDs across different connections,
    enabling self-reply threads to be preserved when crossposting.

    Format: {(source_connection, source_id): {dest_connection: dest_id}}
    Example: {('bluesky', 'at://did.../post/123'): {'mastodon': 'MA1'}}
    """

    message_id_map: dict[tuple[str, str], dict[str, str]] = {}
    message_id_map_lock: Lock = Lock()

    def store_message_mapping(
        self, source_connection: str, source_id: str, dest_id: str
    ) -> None:
        """
        Store a mapping between a source message ID and a destination message ID.

        :param source_connection: Name of the source connection
        :param source_id: ID of the message in the source connection
        :param dest_id: ID of the message in this (destination) connection
        """

        with self.message_id_map_lock:
            key = (source_connection, source_id)

            if key not in self.message_id_map:
                self.message_id_map[key] = {}

            self.message_id_map[key][self.name] = dest_id

            logger.debug(
                "Stored message mapping: %s/%s -> %s/%s",
                source_connection,
                source_id,
                self.name,
                dest_id,
            )

    def resolve_reply_to_id(
        self, source_connection: str, source_id: str
    ) -> Optional[str]:
        """
        Resolve a source message ID to the corresponding ID in this connection.

        :param source_connection: Name of the source connection
        :param source_id: ID of the message in the source connection
        :return: ID in this connection, or None if no mapping exists
        """

        with self.message_id_map_lock:
            key = (source_connection, source_id)
            mapping = self.message_id_map.get(key, {})
            dest_id = mapping.get(self.name)

            if dest_id:
                logger.debug(
                    "Resolved reply: %s/%s -> %s/%s",
                    source_connection,
                    source_id,
                    self.name,
                    dest_id,
                )

            return dest_id
