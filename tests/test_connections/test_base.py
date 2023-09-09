"""
Module for adding unit tests for the base Connection class
and related code.
"""

import pytest

from barkr.connections.base import Connection, ConnectionMode


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
    connection_1.write(["test message"])

    with pytest.raises(NotImplementedError):
        connection_1.read()

    # Write only connection base
    connection_2 = Connection("Write Only", [ConnectionMode.WRITE])
    assert connection_2.name == "Write Only"
    assert connection_2.modes == [ConnectionMode.WRITE]

    assert connection_2.read() == []

    with pytest.raises(NotImplementedError):
        connection_2.write(["test message"])

    # Read/Write connection base
    connection_3 = Connection("Read/Write", [ConnectionMode.READ, ConnectionMode.WRITE])
    assert connection_3.name == "Read/Write"
    assert connection_3.modes == [ConnectionMode.READ, ConnectionMode.WRITE]

    with pytest.raises(NotImplementedError):
        connection_1.read()

    with pytest.raises(NotImplementedError):
        connection_2.write(["test message"])
