"""
Module that implements the main loop of the Barkr application,
enabling users to instance the Barkr class with their own connections
to set crossposting among multiple channels.
"""

import logging
from threading import Lock, Thread

from barkr.connections.base import Connection
from barkr.utils import wrap_while_true

logger = logging.getLogger()


class Barkr:
    """
    Wrapper for the main loop of the application.
    """

    def __init__(self, connections: list[Connection], retry_interval: int = 15) -> None:
        """
        Instantiate a Barkr object with a list of connections, as well as
        internal queues and locks.

        :param connections: A list of connections to be used by the Barkr instance
        :param retry_interval: The interval to wait between retries, in seconds
        """

        if not connections:
            raise ValueError("Must provide at least one connection!")

        self.retry_interval: int = retry_interval

        logger.debug(
            "Initializing Barkr instance with %s connection(s)...", len(connections)
        )
        self.connections: list[Connection] = connections
        self.message_queues: dict[str, list[str]] = {
            connection.name: [] for connection in connections
        }
        self.message_queues_lock: Lock = Lock()
        logger.debug("Barkr instance initialized!")

    def read(self) -> None:
        """
        Read messages from all connections and add them to the message queues
        of other connections
        """

        for connection in self.connections:
            messages = connection.read()

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
            with self.message_queues_lock:
                messages = self.message_queues[connection.name]
                connection.write(messages)
                logger.info(
                    "Posted %s message(s) from %s's queue",
                    len(messages),
                    connection.name,
                )
                self.message_queues[connection.name] = []

    def start(self) -> None:
        """
        Start the Barkr instance
        """

        logger.info("Starting Barkr!")

        read_thread = Thread(target=wrap_while_true(self.read, self.retry_interval))
        write_thread = Thread(target=wrap_while_true(self.write, self.retry_interval))

        read_thread.start()
        write_thread.start()

        logger.info("Barkr started!")

        read_thread.join()
        write_thread.join()

        logger.info("Barkr exiting!")
