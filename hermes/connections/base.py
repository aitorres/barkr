"""
Module to implement the base class and enums for custom
connections to social media networks, chat services, etc.
"""

from enum import Enum


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
    """

    name: str
    modes: list[ConnectionMode]

    def __init__(self, name: str, modes: list[ConnectionMode]) -> None:
        """
        Initializes the connection with a name and a list of modes

        :param name: The name of the connection
        :param modes: A list of modes for the connection
        """

        self.name = name
        self.modes = modes

    def read(self) -> list[str]:
        """
        Read new messages from this connection
        """

        if ConnectionMode.READ not in self.modes:
            return []

        return self._fetch()

    def write(self, messages: list[str]) -> None:
        """
        Write messages to this connection

        :param messages: A list of messages to be posted
        """

        if ConnectionMode.WRITE not in self.modes:
            return

        self._post(messages)

    def _fetch(self) -> list[str]:
        """
        Fetch messages from this connection
        """

        raise NotImplementedError(f"Fetch not implemented for connection {self.name}")

    def _post(self, messages: list[str]) -> None:
        """
        Post messages to this connection

        :param messages: A list of messages to be posted
        """

        raise NotImplementedError(f"Post not implemented for connection {self.name}")
