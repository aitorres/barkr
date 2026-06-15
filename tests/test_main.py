"""
Test module for the main loop of the Barkr app.
"""

from collections import deque

import pytest

from barkr.connections.base import Connection, ConnectionMode
from barkr.main import Barkr
from barkr.models import Message


def _qs(barkr: Barkr) -> dict[str, list[Message]]:
    """Snapshot ``barkr.message_queues`` as a dict of plain lists for assertions."""
    return {name: list(queue) for name, queue in barkr.message_queues.items()}


class ConnectionMockup(Connection):
    """
    Mockup of a connection for testing purposes. Generates predictable messages
    and keeps track of posted messages in a list.
    """

    def __init__(
        self,
        name: str,
        modes: list[ConnectionMode],
        group: str | None = None,
    ) -> None:
        super().__init__(name, modes, group)
        self.posted_messages: list[str] = []
        self.raise_exception_on_write: bool = False

    def _fetch(self) -> list[Message]:
        return [
            Message(
                id=f"{self.name}-Id1",
                message=f"{self.name}-TestMsg1",
                source_connection=self.name,
            ),
            Message(
                id=f"{self.name}-Id2",
                message=f"{self.name}-TestMsg2",
                source_connection=self.name,
            ),
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
    assert _qs(barkr) == {"TestCon1": [], "TestCon2": []}

    barkr.read()
    assert _qs(barkr) == {"TestCon1": [], "TestCon2": []}
    assert test_connection_1.posted_messages == []
    assert test_connection_2.posted_messages == []

    barkr.write()
    assert _qs(barkr) == {"TestCon1": [], "TestCon2": []}
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
    assert _qs(barkr) == {"TestCon1": [], "TestCon2": []}

    barkr.read()
    assert _qs(barkr) == {"TestCon1": [], "TestCon2": []}
    assert test_connection_1.posted_messages == []
    assert test_connection_2.posted_messages == []

    barkr.write()
    assert _qs(barkr) == {"TestCon1": [], "TestCon2": []}
    assert test_connection_1.posted_messages == []
    assert test_connection_2.posted_messages == []

    # forcing messages to appear in the queue
    barkr.message_queues = {
        "TestCon1": deque(
            [
                Message(id="Idx", message="msg1", source_connection="test"),
                Message(id="Idx", message="msg2", source_connection="test"),
            ]
        ),
        "TestCon2": deque(
            [
                Message(id="Idx", message="msg3", source_connection="test"),
                Message(id="Idx", message="msg4", source_connection="test"),
            ]
        ),
    }
    barkr.write()
    assert _qs(barkr) == {"TestCon1": [], "TestCon2": []}
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
    assert _qs(barkr) == {"TestCon1": [], "TestCon2": []}

    barkr.read()
    assert _qs(barkr) == {
        "TestCon1": [],
        "TestCon2": [
            Message(
                id="TestCon1-Id1",
                message="TestCon1-TestMsg1",
                source_connection="TestCon1",
            ),
            Message(
                id="TestCon1-Id2",
                message="TestCon1-TestMsg2",
                source_connection="TestCon1",
            ),
        ],
    }
    assert test_connection_1.posted_messages == []
    assert test_connection_2.posted_messages == []

    barkr.write()
    assert _qs(barkr) == {"TestCon1": [], "TestCon2": []}
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

    barkr.write_message(Message(id="Idx", message="msg1", source_connection="test"))
    assert test_connection_1.posted_messages == ["msg1"]
    assert test_connection_2.posted_messages == ["msg1"]
    assert test_connection_3.posted_messages == []

    barkr.write_message(Message(id="Idx", message="msg2", source_connection="test"))
    assert test_connection_1.posted_messages == ["msg1", "msg2"]
    assert test_connection_2.posted_messages == ["msg1", "msg2"]
    assert test_connection_3.posted_messages == []

    # Handling exceptions per-connection
    test_connection_1.raise_exception_on_write = True
    barkr.write_message(Message(id="Idx", message="msg3", source_connection="test"))
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

    assert _qs(barkr) == {
        "TestCon0": [],
        "TestCon1": [
            Message(
                id="TestCon0-Id1",
                message="TestCon0-TestMsg1",
                source_connection="TestCon0",
            ),
            Message(
                id="TestCon0-Id2",
                message="TestCon0-TestMsg2",
                source_connection="TestCon0",
            ),
        ],
        "TestCon2": [
            Message(
                id="TestCon0-Id1",
                message="TestCon0-TestMsg1",
                source_connection="TestCon0",
            ),
            Message(
                id="TestCon0-Id2",
                message="TestCon0-TestMsg2",
                source_connection="TestCon0",
            ),
        ],
    }

    # writing, this should only write 1 message and leave 1 in the queue
    barkr.write()
    assert _qs(barkr) == {
        "TestCon0": [],
        "TestCon1": [
            Message(
                id="TestCon0-Id2",
                message="TestCon0-TestMsg2",
                source_connection="TestCon0",
            ),
        ],
        "TestCon2": [
            Message(
                id="TestCon0-Id2",
                message="TestCon0-TestMsg2",
                source_connection="TestCon0",
            ),
        ],
    }
    assert test_connection_1.posted_messages == ["TestCon0-TestMsg1"]
    assert test_connection_2.posted_messages == ["TestCon0-TestMsg1"]
    assert test_connection_0.posted_messages == []

    # writing again, this should write the last message
    barkr.write()
    assert _qs(barkr) == {
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
    assert _qs(barkr) == {
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


def test_barkr_default_group_relays_to_all() -> None:
    """
    When no group is provided, every connection lands in the default
    group, preserving the historical behavior of relaying to all destinations.
    """

    reader = ConnectionMockup("Reader", [ConnectionMode.READ])
    writer_1 = ConnectionMockup("Writer1", [ConnectionMode.WRITE])
    writer_2 = ConnectionMockup("Writer2", [ConnectionMode.WRITE])

    # All connections share the same implicit default group.
    assert reader.group == "default"
    assert writer_1.group == "default"
    assert writer_2.group == "default"

    barkr = Barkr([reader, writer_1, writer_2])
    barkr.read()

    expected = [
        Message(
            id="Reader-Id1",
            message="Reader-TestMsg1",
            source_connection="Reader",
        ),
        Message(
            id="Reader-Id2",
            message="Reader-TestMsg2",
            source_connection="Reader",
        ),
    ]
    assert _qs(barkr) == {"Reader": [], "Writer1": expected, "Writer2": expected}


def test_barkr_groups_isolate_routing() -> None:
    """
    Messages from a reader are only relayed to writers in the same group.
    """

    reader_a = ConnectionMockup("ReaderA", [ConnectionMode.READ], group="a")
    writer_a = ConnectionMockup("WriterA", [ConnectionMode.WRITE], group="a")
    reader_b = ConnectionMockup("ReaderB", [ConnectionMode.READ], group="b")
    writer_b = ConnectionMockup("WriterB", [ConnectionMode.WRITE], group="b")

    barkr = Barkr([reader_a, writer_a, reader_b, writer_b])
    barkr.read()

    queues = _qs(barkr)

    # Writer A only received Reader A's messages.
    assert queues["WriterA"] == [
        Message(
            id="ReaderA-Id1",
            message="ReaderA-TestMsg1",
            source_connection="ReaderA",
        ),
        Message(
            id="ReaderA-Id2",
            message="ReaderA-TestMsg2",
            source_connection="ReaderA",
        ),
    ]

    # Writer B only received Reader B's messages.
    assert queues["WriterB"] == [
        Message(
            id="ReaderB-Id1",
            message="ReaderB-TestMsg1",
            source_connection="ReaderB",
        ),
        Message(
            id="ReaderB-Id2",
            message="ReaderB-TestMsg2",
            source_connection="ReaderB",
        ),
    ]

    # Readers never accumulate messages in their own queues.
    assert queues["ReaderA"] == []
    assert queues["ReaderB"] == []


def test_barkr_group_does_not_relay_to_other_group_writer() -> None:
    """
    A writer in a different group from the reader receives nothing, even when it
    is the only writer available.
    """

    reader = ConnectionMockup("Reader", [ConnectionMode.READ], group="group-1")
    writer = ConnectionMockup("Writer", [ConnectionMode.WRITE], group="group-2")

    barkr = Barkr([reader, writer])
    barkr.read()

    assert _qs(barkr) == {"Reader": [], "Writer": []}


def test_barkr_default_group_isolated_from_named_group() -> None:
    """
    A connection left in the default group does not exchange messages with a
    connection placed in an explicit, differently-named group.
    """

    default_reader = ConnectionMockup("DefaultReader", [ConnectionMode.READ])
    named_writer = ConnectionMockup(
        "NamedWriter", [ConnectionMode.WRITE], group="named"
    )

    barkr = Barkr([default_reader, named_writer])
    barkr.read()

    assert _qs(barkr) == {"DefaultReader": [], "NamedWriter": []}


def test_barkr_reader_relays_within_group_only_when_mixed() -> None:
    """
    With one reader and writers split across groups, only the same-group writer
    receives the reader's messages.
    """

    reader = ConnectionMockup("Reader", [ConnectionMode.READ], group="shared")
    same_group_writer = ConnectionMockup(
        "SameWriter", [ConnectionMode.WRITE], group="shared"
    )
    other_group_writer = ConnectionMockup(
        "OtherWriter", [ConnectionMode.WRITE], group="other"
    )
    default_writer = ConnectionMockup("DefaultWriter", [ConnectionMode.WRITE])

    barkr = Barkr([reader, same_group_writer, other_group_writer, default_writer])
    barkr.read()

    queues = _qs(barkr)
    expected = [
        Message(
            id="Reader-Id1",
            message="Reader-TestMsg1",
            source_connection="Reader",
        ),
        Message(
            id="Reader-Id2",
            message="Reader-TestMsg2",
            source_connection="Reader",
        ),
    ]
    assert queues["SameWriter"] == expected
    assert queues["OtherWriter"] == []
    assert queues["DefaultWriter"] == []


def test_barkr_read_write_within_group_end_to_end() -> None:
    """
    A grouped read/write pair delivers messages end-to-end while an unrelated
    group remains untouched.
    """

    reader_a = ConnectionMockup("ReaderA", [ConnectionMode.READ], group="a")
    writer_a = ConnectionMockup("WriterA", [ConnectionMode.WRITE], group="a")
    writer_b = ConnectionMockup("WriterB", [ConnectionMode.WRITE], group="b")

    barkr = Barkr([reader_a, writer_a, writer_b])
    barkr.read()
    barkr.write()

    assert writer_a.posted_messages == ["ReaderA-TestMsg1", "ReaderA-TestMsg2"]
    assert writer_b.posted_messages == []
    assert _qs(barkr) == {"ReaderA": [], "WriterA": [], "WriterB": []}
