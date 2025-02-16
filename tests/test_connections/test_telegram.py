"""
Module to implement unit tests for the Telegram connection class
"""

import pytest

from barkr.connections import ConnectionMode, TelegramConnection


def test_telegram_connection() -> None:
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
    assert telegram.posted_message_ids == set()
    assert not telegram.read()
