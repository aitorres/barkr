"""
Test module for the main loop of the Barkr app.
"""

import pytest

from barkr.connections.base import Connection, ConnectionMode
from barkr.main import Barkr


class ConnectionMockup(Connection):
    """
    Mockup of a connection for testing purposes. Generates predictable messages
    and keeps track of posted messages in a list.
    """

    def __init__(self, name: str, modes: list[ConnectionMode]) -> None:
        super().__init__(name, modes)
        self.posted_messages: list[str] = []

    def _fetch(self) -> list[str]:
        return [f"{self.name}-TestMsg1", f"{self.name}-TestMsg2"]

    def _post(self, messages: list[str]) -> None:
        self.posted_messages += messages


def test_barkr_no_connections() -> None:
    """
    Test the Barkr class with no connections.
    A `ValueError` exception is expected.
    """

    with pytest.raises(ValueError):
        Barkr([])


def test_barkr_read_only() -> None:
    """
    Test the Barkr class with two read-only connections.
    """

    test_connection_1 = ConnectionMockup("TestCon1", [ConnectionMode.READ])
    test_connection_2 = ConnectionMockup("TestCon2", [ConnectionMode.READ])
    barkr = Barkr([test_connection_1, test_connection_2])
    assert barkr.connections == [test_connection_1, test_connection_2]
    assert barkr.message_queues == {"TestCon1": [], "TestCon2": []}

    barkr.read()
    assert barkr.message_queues == {
        "TestCon1": ["TestCon2-TestMsg1", "TestCon2-TestMsg2"],
        "TestCon2": ["TestCon1-TestMsg1", "TestCon1-TestMsg2"],
    }
    assert test_connection_1.posted_messages == []
    assert test_connection_2.posted_messages == []

    barkr.write()
    assert barkr.message_queues == {"TestCon1": [], "TestCon2": []}
    assert test_connection_1.posted_messages == []
    assert test_connection_2.posted_messages == []


def test_barkr_write_only() -> None:
    """
    Test the Barkr class with two write-only connections.
    """

    test_connection_1 = ConnectionMockup("TestCon1", [ConnectionMode.WRITE])
    test_connection_2 = ConnectionMockup("TestCon2", [ConnectionMode.WRITE])
    barkr = Barkr([test_connection_1, test_connection_2])
    assert barkr.connections == [test_connection_1, test_connection_2]
    assert barkr.message_queues == {"TestCon1": [], "TestCon2": []}

    barkr.read()
    assert barkr.message_queues == {"TestCon1": [], "TestCon2": []}
    assert test_connection_1.posted_messages == []
    assert test_connection_2.posted_messages == []

    barkr.write()
    assert barkr.message_queues == {"TestCon1": [], "TestCon2": []}
    assert test_connection_1.posted_messages == []
    assert test_connection_2.posted_messages == []

    # forcing messages to appear in the queue
    barkr.message_queues = {"TestCon1": ["msg1", "msg2"], "TestCon2": ["msg3", "msg4"]}
    barkr.write()
    assert barkr.message_queues == {"TestCon1": [], "TestCon2": []}
    assert test_connection_1.posted_messages == ["msg1", "msg2"]
    assert test_connection_2.posted_messages == ["msg3", "msg4"]


def test_barkr_read_write() -> None:
    """
    Test the Barkr class with a read (source) connection and a write (destination)
    connection simultaneously.
    """

    test_connection_1 = ConnectionMockup("TestCon1", [ConnectionMode.READ])
    test_connection_2 = ConnectionMockup("TestCon2", [ConnectionMode.WRITE])
    barkr = Barkr([test_connection_1, test_connection_2])
    assert barkr.connections == [test_connection_1, test_connection_2]
    assert barkr.message_queues == {"TestCon1": [], "TestCon2": []}

    barkr.read()
    assert barkr.message_queues == {
        "TestCon1": [],
        "TestCon2": ["TestCon1-TestMsg1", "TestCon1-TestMsg2"],
    }
    assert test_connection_1.posted_messages == []
    assert test_connection_2.posted_messages == []

    barkr.write()
    assert barkr.message_queues == {"TestCon1": [], "TestCon2": []}
    assert test_connection_1.posted_messages == []
    assert test_connection_2.posted_messages == [
        "TestCon1-TestMsg1",
        "TestCon1-TestMsg2",
    ]
