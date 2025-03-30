"""
Module that implements the main loop of the Barkr application,
enabling users to instance the Barkr class with their own connections
to set crossposting among multiple channels.
"""

import logging
from threading import Lock, Thread
from typing import Optional

from barkr.connections import Connection, ConnectionMode
from barkr.models import Message
from barkr.utils import wrap_while_true

logger = logging.getLogger()


class Barkr:
    """
    Wrapper for the main loop of the application.
    """

    polling_interval: int
    write_rate_limit: Optional[int]
    connections: list[Connection]
    message_queues: dict[str, list[Message]]
    message_queues_lock: Lock

    def __init__(
        self,
        connections: list[Connection],
        polling_interval: int = 10,
        write_rate_limit: Optional[int] = None,
    ) -> None:
        """
        Instantiate a Barkr object with a list of connections, as well as
        internal queues and locks.

        If a `write_rate_limit` is provided, Barkr will only write up to that
        many messages per write-thread polling interval.

        :param connections: A list of connections to be used by the Barkr instance
        :param polling_interval: The interval to wait between polling requests, in seconds
        :param write_rate_limit: (optional) The rate limit for writing messages
        """

        if not connections:
            raise ValueError("Must provide at least one connection!")

        if polling_interval < 1:
            raise ValueError("Polling interval must be at least 1 second!")

        if write_rate_limit is not None and write_rate_limit < 1:
            raise ValueError(
                "If specified, write rate limit must be at least 1 message!"
            )

        self.polling_interval: int = polling_interval
        self.write_rate_limit: Optional[int] = write_rate_limit

        logger.info(
            "Initializing Barkr instance with %s connection(s)...", len(connections)
        )
        self.connections = connections
        self.message_queues = {connection.name: [] for connection in connections}
        self.message_queues_lock = Lock()
        logger.info("Barkr instance initialized!")

    def read(self) -> None:
        """
        Read messages from all connections and add them to the message queues
        of other connections
        """

        for connection in self.connections:
            # Reading is only allowed for connections with the READ mode
            if ConnectionMode.READ not in connection.modes:
                continue

            messages = connection.read()

            if messages:
                with self.message_queues_lock:
                    for name in self.message_queues:
                        if name != connection.name:
                            self.message_queues[name] += messages
                            logger.info(
                                "Added %s message(s) from %s to %s queue",
                                len(messages),
                                connection.name,
                                name,
                            )

    def write(self) -> None:
        """
        Write messages from the message queues to all connections
        """

        for connection in self.connections:
            max_amount: int = self.write_rate_limit or len(
                self.message_queues[connection.name]
            )

            # Writing is only allowed for connections with the WRITE mode
            if ConnectionMode.WRITE in connection.modes:
                with self.message_queues_lock:
                    messages = self.message_queues[connection.name][:max_amount]
                    n_messages = len(messages)
                    logger.info(
                        "Writing %s message(s) from %s's queue "
                        "(%s messages remaining after that)",
                        n_messages,
                        connection.name,
                        len(self.message_queues[connection.name]) - n_messages,
                    )

                    if messages:
                        connection.write(messages)
                        logger.info(
                            "Posted %s message(s) from %s's queue",
                            n_messages,
                            connection.name,
                        )

            # Clear sent messages from the queue for the current connection
            with self.message_queues_lock:
                self.message_queues[connection.name] = self.message_queues[
                    connection.name
                ][max_amount:]

    def write_message(self, message: Message) -> None:
        """
        Write a single message to all connections. Barkr does not need
        to be running on a loop for this to work.


        Useful if your use case does not require a read-write loop,
        and for testing purposes.

        :param message: The message to be sent
        """

        logger.info("Writing message to all connections...")

        for connection in self.connections:
            if ConnectionMode.WRITE in connection.modes:
                try:
                    connection.write([message])
                except Exception as e:  # pylint: disable=broad-except
                    logger.error("Error posting message to %s: %s", connection.name, e)
                    continue
                else:
                    logger.info("Posted message to %s", connection.name)

        logger.info("Message posted to all connections!")

    def start(self) -> None:
        """
        Start the Barkr instance
        """

        logger.info("Starting Barkr!")

        read_thread = Thread(target=wrap_while_true(self.read, self.polling_interval))
        write_thread = Thread(target=wrap_while_true(self.write, self.polling_interval))

        read_thread.start()
        write_thread.start()
        logger.info("Barkr started!")

        read_thread.join()
        write_thread.join()
        logger.info("Barkr exiting!")
