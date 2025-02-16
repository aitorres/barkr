"""
Module to implement unit tests for the Discord connection class
"""

import pytest

from barkr.connections import ConnectionMode, DiscordConnection


def test_discord_connection() -> None:
    """
    Basic unit tests for the DiscordConnection class
    """

    with pytest.raises(
        NotImplementedError, match="DiscordConnection only supports write mode."
    ):
        DiscordConnection(
            "DiscordClass", [ConnectionMode.READ], "test_token", 1234567890
        )

    with pytest.raises(
        NotImplementedError, match="DiscordConnection only supports write mode."
    ):
        DiscordConnection(
            "DiscordClass",
            [ConnectionMode.READ, ConnectionMode.WRITE],
            "test_token",
            1234567890,
        )

    discord_connection = DiscordConnection(
        "Discord Connection", [ConnectionMode.WRITE], "test_token", 1234567890
    )
    assert discord_connection.name == "Discord Connection"
    assert discord_connection.token == "test_token"
    assert discord_connection.channel_id == 1234567890
    assert discord_connection.posted_message_ids == set()

    # Reading never returns anything other than an empty list
    assert not discord_connection.read()
