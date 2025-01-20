"""
Module for adding unit tests for the base Connection class
and related code.
"""

import pytest

from barkr.connections.base import Connection, ConnectionMode
from barkr.models.message import Message


def test_connection() -> None:
    """
    Tests the base implementation of the Connection class,
    including safeguards against using modes that haven't
    been implemented.
    """

    # Read only connection base
    connection_1 = Connection("Read Only", [ConnectionMode.READ])
    assert connection_1.name == "Read Only"
    assert connection_1.modes == [ConnectionMode.READ]

    # This shouldn't raise any exceptions
    connection_1.write([Message(id="id1", message="test message")])

    with pytest.raises(NotImplementedError):
        connection_1.read()

    # Write only connection base
    connection_2 = Connection("Write Only", [ConnectionMode.WRITE])
    assert connection_2.name == "Write Only"
    assert connection_2.modes == [ConnectionMode.WRITE]

    assert not connection_2.read()

    with pytest.raises(NotImplementedError):
        connection_2.write([Message(id="id1", message="test message")])

    # Read/Write connection base
    connection_3 = Connection("Read/Write", [ConnectionMode.READ, ConnectionMode.WRITE])
    assert connection_3.name == "Read/Write"
    assert connection_3.modes == [ConnectionMode.READ, ConnectionMode.WRITE]

    with pytest.raises(NotImplementedError):
        connection_1.read()

    with pytest.raises(NotImplementedError):
        connection_2.write([Message(id="id1", message="test message")])


def test_connection_mode() -> None:
    """Tests that at least one mode is required for a connection"""

    with pytest.raises(
        ValueError, match="At least one mode must be provided for the connection."
    ):
        Connection("No Modes", [])


def test_connection_handles_message_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Tests that the Connection class handles message IDs correctly
    in order to avoid posting duplicate messages.

    We want to avoid situations like the following:
    1. The connection posts a message with a given ID, say, abc123. We assume
       that at this time, other connections have also posted the same message.
    2. The connection fetches new messages, including the one with ID abc123
    3. The connection enqueues the message with ID abc123 to be posted again
       by other connections, leading to duplicate posts.
    """

    connection = Connection("Read/Write", [ConnectionMode.READ, ConnectionMode.WRITE])

    # Mock the _fetch method to return a list of messages with IDs 1, 2, and 3
    def mock_fetch() -> list[Message]:
        return [
            Message(id="1", message="test message 1"),
            Message(id="2", message="test message 2"),
            Message(id="3", message="test message 3"),
        ]

    monkeypatch.setattr(connection, "_fetch", mock_fetch)

    # Mock the _post method to add the message ID to the posted_message_ids set
    # and return the message ID
    posted_message_ids = []

    def mock_post(messages: list[Message]) -> list[str]:
        for message in messages:
            posted_message_ids.append(message.id)
        return posted_message_ids

    monkeypatch.setattr(connection, "_post", mock_post)

    # Assert initial state
    assert connection.posted_message_ids == set()
    assert not posted_message_ids

    # Post the messages
    connection.write(
        [
            Message(id="1", message="test message 1"),
            Message(id="2", message="test message 2"),
            Message(id="3", message="test message 3"),
        ]
    )
    assert connection.posted_message_ids == {"1", "2", "3"}
    assert posted_message_ids == ["1", "2", "3"]

    # Fetch the messages again and assert nothing is enqueued
    new_messages = connection.read()
    assert not new_messages

    # Post a new message
    connection.write(
        [
            Message(id="4", message="test message 4"),
        ]
    )
    assert connection.posted_message_ids == {"1", "2", "3", "4"}
    assert posted_message_ids == ["1", "2", "3", "4"]
