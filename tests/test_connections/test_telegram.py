"""
Module to implement unit tests for the Telegram connection class
"""

from typing import Any

import pytest

from barkr.connections import ConnectionMode, TelegramConnection
from barkr.models.message import Message


def test_telegram_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Basic unit tests for the TelegramConnection class
    """

    with pytest.raises(
        NotImplementedError, match="TelegramConnection only supports write mode."
    ):
        TelegramConnection(
            "TelegramClass",
            [ConnectionMode.READ],
            "test_token",
            "test_chat_id",
        )

    with pytest.raises(
        NotImplementedError, match="TelegramConnection only supports write mode."
    ):
        TelegramConnection(
            "TelegramClass",
            [ConnectionMode.READ, ConnectionMode.WRITE],
            "test_token",
            "test_chat_id",
        )

    # Reading never returns anything other than an empty list
    telegram = TelegramConnection(
        "Telegram Connection",
        [ConnectionMode.WRITE],
        "test_token",
        "test_chat_id",
    )
    assert telegram.name == "Telegram Connection"
    assert telegram.modes == [ConnectionMode.WRITE]
    assert telegram.posted_message_ids == set()
    assert not telegram.read()

    message_count: int = 0

    def mock_send_message(*_args: Any, **_kwargs: Any) -> None:
        """
        Mock function to simulate sending a message
        """
        nonlocal message_count
        message_count += 1

    monkeypatch.setattr("asyncio.run", mock_send_message)

    assert message_count == 0
    telegram.write([Message("test_id", "test message")])
    assert message_count == 1

    telegram.write([Message("test_id", "test message")])
    assert message_count == 2
