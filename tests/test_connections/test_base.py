"""
Module for adding unit tests for the base Connection class
and related code.
"""

import pytest

from barkr.connections import Connection, ConnectionMode
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


def test_connection_handles_posted_message_ids(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_connection_avoids_infinite_loops(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Tests that the Connection class can avoid infinite loops between
    multiple connections that are set to read and write.

    For example, if we have Connection A and Connection B both set to
    read/write mode, we want to avoid:
    1. Connection A fetching a message with content X and enqueueing it
       for other connections.
    2. Connection B posting a message with content X.
    3. Connection B fetching a message with content X (the one that it just posted)
       and enqueueing it for others
    4. Connection A fetching a message with content X...
    """

    # Setting up the two connections
    connection_a = Connection(
        "Connection A", [ConnectionMode.READ, ConnectionMode.WRITE]
    )
    connection_b = Connection(
        "Connection B", [ConnectionMode.READ, ConnectionMode.WRITE]
    )
    posted_by_b = []

    # First mock: Connection A fetches messages with IDs 1, 2, and 3
    def mock_fetch_a() -> list[Message]:
        return [
            Message(id="1", message="test message 1"),
            Message(id="2", message="test message 2"),
            Message(id="3", message="test message 3"),
        ]

    monkeypatch.setattr(connection_a, "_fetch", mock_fetch_a)

    messages = connection_a.read()
    assert len(messages) == 3
    assert [message.id for message in messages] == ["1", "2", "3"]

    # Second mock: Connection B posts messages read from A
    def mock_post_b(messages: list[Message]) -> list[str]:
        for message in messages:
            posted_by_b.append(message.id + "-b")
        return posted_by_b

    monkeypatch.setattr(connection_b, "_post", mock_post_b)

    connection_b.write(messages)

    # Third mock: Connection B fetches messages with its new IDs
    def mock_fetch_b() -> list[Message]:
        return [
            Message(id="1-b", message="test message 1"),
            Message(id="2-b", message="test message 2"),
            Message(id="3-b", message="test message 3"),
        ]

    monkeypatch.setattr(connection_b, "_fetch", mock_fetch_b)

    # We shouldn't bring anything here and this should stop the loop
    messages = connection_b.read()
    assert not messages


def test_connection_handles_read_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test that the Connection class can recover from an exception
    when attempting to read messages.
    """

    connection = Connection("Read", [ConnectionMode.READ])

    attempts = 0

    def mock_fetch_a() -> list[Message]:
        nonlocal attempts
        attempts += 1

        if attempts == 1:
            raise ValueError("Test exception")
        return [
            Message(id="1", message="test message 1"),
            Message(id="2", message="test message 2"),
            Message(id="3", message="test message 3"),
        ]

    monkeypatch.setattr(connection, "_fetch", mock_fetch_a)

    # First attempt will raise an exception that will be caught
    # with no messages returned
    messages = connection.read()
    assert not messages

    # Second attempt will return the messages
    messages = connection.read()
    assert len(messages) == 3
    assert [message.id for message in messages] == ["1", "2", "3"]

    # But if it's a NotImplementedError, it should be raised
    def mock_fetch_b() -> list[Message]:
        raise NotImplementedError("Test NotImplementedError")

    monkeypatch.setattr(connection, "_fetch", mock_fetch_b)

    with pytest.raises(NotImplementedError):
        connection.read()
