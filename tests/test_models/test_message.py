"""
Module to implement unit tests for the Message class.
"""

from barkr.models.message import Message


def test_message() -> None:
    """
    Test that the Message class is initialized correctly
    """

    message_1 = Message(
        id="12345", message="Hello, world!", language="en", label="greeting"
    )

    assert message_1.id == "12345"
    assert message_1.message == "Hello, world!"
    assert message_1.language == "en"
    assert message_1.label == "greeting"

    message_2 = Message(
        id="67890",
        message="Bonjour le monde!",
    )
    assert message_2.id == "67890"
    assert message_2.message == "Bonjour le monde!"
    assert message_2.language is None
    assert message_2.label is None


def test_message_has_content() -> None:
    """
    Test that the has_content method appropriately
    tells if the Message contains content or not.
    """

    assert Message(id="12345", message="Hello, world!").has_content()
    assert not Message(id="12345", message="").has_content()
    assert not Message(id="12345", message="   ").has_content()
    assert not Message(id="12345", message="\n").has_content()
