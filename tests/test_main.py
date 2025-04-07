"""
Test module for the main loop of the Barkr app.
"""

import pytest

from barkr.connections.base import Connection, ConnectionMode
from barkr.main import Barkr
from barkr.models import Message


class ConnectionMockup(Connection):
    """
    Mockup of a connection for testing purposes. Generates predictable messages
    and keeps track of posted messages in a list.
    """

    def __init__(self, name: str, modes: list[ConnectionMode]) -> None:
        super().__init__(name, modes)
        self.posted_messages: list[str] = []
        self.raise_exception_on_write: bool = False

    def _fetch(self) -> list[Message]:
        return [
            Message(id=f"{self.name}-Id1", message=f"{self.name}-TestMsg1"),
            Message(id=f"{self.name}-Id2", message=f"{self.name}-TestMsg2"),
        ]

    def _post(self, messages: list[Message]) -> list[str]:
        if self.raise_exception_on_write:
            raise NotImplementedError("Simulated exception on write")

        self.posted_messages += [m.message for m in messages]
        return [f"id-{i}" for i in range(len(messages))]


def test_barkr_no_connections() -> None:
    """
    Test the Barkr class with no connections.
    A `ValueError` exception is expected.
    """

    with pytest.raises(ValueError):
        Barkr([])


def test_barkr_invalid_polling_interval() -> None:
    """
    Test the Barkr class with an invalid polling interval.
    A `ValueError` exception is expected.
    """

    with pytest.raises(ValueError):
        Barkr([ConnectionMockup("TestCon", [ConnectionMode.READ])], 0)

    with pytest.raises(ValueError):
        Barkr([ConnectionMockup("TestCon", [ConnectionMode.READ])], -1)


def test_barkr_invalid_write_rate_limit() -> None:
    """
    Test the Barkr class with an invalid write rate limit.
    A `ValueError` exception is expected.
    """

    with pytest.raises(ValueError):
        Barkr([ConnectionMockup("TestCon", [ConnectionMode.READ])], 10, 0)

    with pytest.raises(ValueError):
        Barkr([ConnectionMockup("TestCon", [ConnectionMode.READ])], 10, -1)


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
        "TestCon1": [
            Message(id="TestCon2-Id1", message="TestCon2-TestMsg1"),
            Message(id="TestCon2-Id2", message="TestCon2-TestMsg2"),
        ],
        "TestCon2": [
            Message(id="TestCon1-Id1", message="TestCon1-TestMsg1"),
            Message(id="TestCon1-Id2", message="TestCon1-TestMsg2"),
        ],
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
    barkr.message_queues = {
        "TestCon1": [
            Message(id="Idx", message="msg1"),
            Message(id="Idx", message="msg2"),
        ],
        "TestCon2": [
            Message(id="Idx", message="msg3"),
            Message(id="Idx", message="msg4"),
        ],
    }
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
        "TestCon2": [
            Message(id="TestCon1-Id1", message="TestCon1-TestMsg1"),
            Message(id="TestCon1-Id2", message="TestCon1-TestMsg2"),
        ],
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


def test_barkr_write_message() -> None:
    """
    Test the Barkr class's behavior when using the `write_message` method,
    that does not require the main app to be started or a loop
    to be running.
    """

    test_connection_1 = ConnectionMockup("TestCon1", [ConnectionMode.WRITE])
    test_connection_2 = ConnectionMockup("TestCon2", [ConnectionMode.WRITE])
    test_connection_3 = ConnectionMockup("TestCon3", [ConnectionMode.READ])

    barkr = Barkr([test_connection_1, test_connection_2, test_connection_3])
    assert barkr.connections == [
        test_connection_1,
        test_connection_2,
        test_connection_3,
    ]

    barkr.write_message(Message(id="Idx", message="msg1"))
    assert test_connection_1.posted_messages == ["msg1"]
    assert test_connection_2.posted_messages == ["msg1"]
    assert test_connection_3.posted_messages == []

    barkr.write_message(Message(id="Idx", message="msg2"))
    assert test_connection_1.posted_messages == ["msg1", "msg2"]
    assert test_connection_2.posted_messages == ["msg1", "msg2"]
    assert test_connection_3.posted_messages == []

    # Handling exceptions per-connection
    test_connection_1.raise_exception_on_write = True
    barkr.write_message(Message(id="Idx", message="msg3"))
    assert test_connection_1.posted_messages == ["msg1", "msg2"]
    assert test_connection_2.posted_messages == ["msg1", "msg2", "msg3"]
    assert test_connection_3.posted_messages == []


def test_barkr_write_rate_limit() -> None:
    """
    Tests the Barkr's class behavior when setting up a write rate limit.
    """

    test_connection_0 = ConnectionMockup("TestCon0", [ConnectionMode.READ])
    test_connection_1 = ConnectionMockup("TestCon1", [ConnectionMode.WRITE])
    test_connection_2 = ConnectionMockup("TestCon2", [ConnectionMode.WRITE])

    barkr = Barkr(
        [test_connection_0, test_connection_1, test_connection_2], write_rate_limit=1
    )
    assert barkr.connections == [
        test_connection_0,
        test_connection_1,
        test_connection_2,
    ]

    # enqueuing 2 messages
    barkr.read()

    assert barkr.message_queues == {
        "TestCon0": [],
        "TestCon1": [
            Message(id="TestCon0-Id1", message="TestCon0-TestMsg1"),
            Message(id="TestCon0-Id2", message="TestCon0-TestMsg2"),
        ],
        "TestCon2": [
            Message(id="TestCon0-Id1", message="TestCon0-TestMsg1"),
            Message(id="TestCon0-Id2", message="TestCon0-TestMsg2"),
        ],
    }

    # writing, this should only write 1 message and leave 1 in the queue
    barkr.write()
    assert barkr.message_queues == {
        "TestCon0": [],
        "TestCon1": [
            Message(id="TestCon0-Id2", message="TestCon0-TestMsg2"),
        ],
        "TestCon2": [
            Message(id="TestCon0-Id2", message="TestCon0-TestMsg2"),
        ],
    }
    assert test_connection_1.posted_messages == ["TestCon0-TestMsg1"]
    assert test_connection_2.posted_messages == ["TestCon0-TestMsg1"]
    assert test_connection_0.posted_messages == []

    # writing again, this should write the last message
    barkr.write()
    assert barkr.message_queues == {
        "TestCon0": [],
        "TestCon1": [],
        "TestCon2": [],
    }
    assert test_connection_1.posted_messages == [
        "TestCon0-TestMsg1",
        "TestCon0-TestMsg2",
    ]
    assert test_connection_2.posted_messages == [
        "TestCon0-TestMsg1",
        "TestCon0-TestMsg2",
    ]

    # one more, should not write anything new
    barkr.write()
    assert barkr.message_queues == {
        "TestCon0": [],
        "TestCon1": [],
        "TestCon2": [],
    }
    assert test_connection_1.posted_messages == [
        "TestCon0-TestMsg1",
        "TestCon0-TestMsg2",
    ]
    assert test_connection_2.posted_messages == [
        "TestCon0-TestMsg1",
        "TestCon0-TestMsg2",
    ]
