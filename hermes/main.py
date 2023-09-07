"""
Module that implements the main loop of the Hermes application,
enabling users to instance the Hermes class with their own connections
to set crossposting among multiple channels.
"""

import logging
from threading import Lock, Thread

from hermes.connections.base import Connection

logger = logging.getLogger()


class Hermes:
    """
    Wrapper for the main loop of the application.
    """

    def __init__(self, connections: list[Connection]) -> None:
        """
        Instantiate a Hermes object with a list of connections, as well as
        internal queues and locks.
        """

        if not connections:
            raise ValueError("Must provide at least one connection!")

        logger.debug(
            "Initializing Hermes instance with %s connection(s)...", len(connections)
        )
        self.connections: list[Connection] = connections
        self.message_queues: dict[str, list[str]] = {
            connection.name: [] for connection in connections
        }
        self.message_queues_lock: Lock = Lock()
        logger.debug("Hermes instance initialized!")

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
                    "Posted %s message(s) from %s", len(messages), connection.name
                )
                self.message_queues[connection.name] = []

    def start(self) -> None:
        """
        Start the Hermes instance
        """

        logger.info("Starting Hermes!")

        read_thread = Thread(target=self.read)
        write_thread = Thread(target=self.write)

        read_thread.start()
        write_thread.start()

        logger.info("Hermes started!")

        read_thread.join()
        write_thread.join()

        logger.info("Hermes exiting!")
