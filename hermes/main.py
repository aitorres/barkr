"""
Module that implements the main loop of the Hermes application,
enabling users to instance the Hermes class with their own connections
to set crossposting among multiple channels.
"""

from threading import Lock, Thread

from hermes.connections.base import Connection


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

        self.connections: list[Connection] = connections
        self.message_queues: dict[str, list[str]] = {
            connection.name: [] for connection in connections
        }
        self.message_queues_lock: Lock = Lock()

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

    def write(self) -> None:
        """
        Write messages from the message queues to all connections
        """

        for connection in self.connections:
            with self.message_queues_lock:
                messages = self.message_queues[connection.name]
                connection.write(messages)
                self.message_queues[connection.name] = []

    def start(self) -> None:
        """
        Start the Hermes instance
        """

        print("Starting!")

        read_thread = Thread(target=self.read)
        write_thread = Thread(target=self.write)

        read_thread.start()
        write_thread.start()

        read_thread.join()
        write_thread.join()

        print("Done!")
