"""
Module to implement unit tests for the Discord connection class
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from barkr.connections import ConnectionMode, DiscordConnection
from barkr.models import Message
from barkr.models.message_mention import MessageMention
from barkr.models.message_metadata import MessageMetadata


@pytest.fixture(name="discord_client")
def mock_discord_client(monkeypatch: pytest.MonkeyPatch) -> discord.Client:
    """Use the real client lifecycle with mocked network operations."""
    client = discord.Client(intents=discord.Intents.default())
    monkeypatch.setattr(client, "login", AsyncMock())
    monkeypatch.setattr(
        client, "fetch_channel", AsyncMock(return_value=Mock(spec=discord.TextChannel))
    )
    monkeypatch.setattr(client, "start", AsyncMock())
    monkeypatch.setattr("discord.Client", Mock(return_value=client))
    return client


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


def test_discord_send_messages(discord_client: discord.Client) -> None:
    """Send messages once without opening a gateway connection."""

    assert isinstance(discord_client.login, AsyncMock)
    assert isinstance(discord_client.fetch_channel, AsyncMock)
    assert isinstance(discord_client.start, AsyncMock)

    connection = DiscordConnection(
        "Discord Connection", [ConnectionMode.WRITE], "test_token", 1234567890
    )

    asyncio.run(
        connection._send_messages(  # pylint: disable=protected-access
            [
                Message("1", "hello", "source"),
                Message("2", "world", "source"),
            ]
        )
    )

    discord_client.login.assert_awaited_once_with("test_token")
    discord_client.fetch_channel.assert_awaited_once_with(1234567890)
    assert [
        call.args[0]
        for call in discord_client.fetch_channel.return_value.send.await_args_list
    ] == ["hello", "world"]
    discord_client.start.assert_not_called()
    assert discord_client.is_closed()


@pytest.mark.parametrize("fails", [False, True])
def test_discord_post_closes_event_loop(
    monkeypatch: pytest.MonkeyPatch, fails: bool
) -> None:
    """Close the event loop on success and when a send raises an error."""

    received_messages: list[list[Message]] = []
    loops: list[asyncio.AbstractEventLoop] = []

    async def mock_send_messages(_, messages: list[Message]) -> None:
        received_messages.append(messages)
        loops.append(asyncio.get_running_loop())
        if fails:
            raise RuntimeError("Send failed")

    monkeypatch.setattr(
        DiscordConnection,
        "_send_messages",
        mock_send_messages,
    )

    connection = DiscordConnection(
        "Discord Connection", [ConnectionMode.WRITE], "test_token", 1234567890
    )
    messages = [Message("1", "hello", "source")]

    if fails:
        with pytest.raises(RuntimeError, match="Send failed"):
            connection.write(messages)
    else:
        connection.write(messages)
    assert received_messages == [messages]
    assert len(loops) == 1
    assert loops[0].is_closed()


@pytest.mark.parametrize("operation", ["login", "fetch_channel", "send"])
def test_discord_failure_closes_client(
    discord_client: discord.Client, operation: str
) -> None:
    """Return network errors to the caller and close the client."""
    assert isinstance(discord_client.fetch_channel, AsyncMock)
    assert isinstance(discord_client.start, AsyncMock)

    error = discord.Forbidden(Mock(status=403, reason="Forbidden"), "Access denied")
    if operation == "send":
        target = discord_client.fetch_channel.return_value.send
        target.side_effect = [None, error]
    else:
        target = getattr(discord_client, operation)
        target.side_effect = error

    connection = DiscordConnection(
        "Discord Connection", [ConnectionMode.WRITE], "test_token", 1234567890
    )
    with pytest.raises(discord.Forbidden) as caught:
        connection.write(
            [
                Message("1", "hello", "source"),
                Message("2", "world", "source"),
                Message("3", "not sent", "source"),
            ]
        )

    assert caught.value is error
    assert target.await_count == (2 if operation == "send" else 1)
    assert discord_client.is_closed()
    discord_client.start.assert_not_called()


def test_discord_missing_channel_closes_client(discord_client: discord.Client) -> None:
    """Return a missing-channel error instead of waiting for another ready event."""
    assert isinstance(discord_client.fetch_channel, AsyncMock)

    error = discord.NotFound(Mock(status=404, reason="Not Found"), "Unknown Channel")
    discord_client.fetch_channel.side_effect = error
    connection = DiscordConnection(
        "Discord Connection", [ConnectionMode.WRITE], "test_token", 1234567890
    )

    with pytest.raises(discord.NotFound) as caught:
        connection.write([Message("1", "hello", "source")])

    assert caught.value is error
    assert discord_client.is_closed()


def test_discord_non_messageable_channel(discord_client: discord.Client) -> None:
    """Reject channel types that cannot receive messages and close the client."""
    assert isinstance(discord_client.fetch_channel, AsyncMock)

    discord_client.fetch_channel.return_value = Mock(spec=discord.CategoryChannel)
    connection = DiscordConnection(
        "Discord Connection", [ConnectionMode.WRITE], "test_token", 1234567890
    )

    with pytest.raises(TypeError, match="does not support messages"):
        connection.write([Message("1", "hello", "source")])

    assert discord_client.is_closed()


def test_discord_renders_mentions_with_profile_url(
    discord_client: discord.Client,
) -> None:
    """Mention metadata is rendered as markdown links on Discord."""

    assert isinstance(discord_client.fetch_channel, AsyncMock)

    connection = DiscordConnection(
        "Discord Connection", [ConnectionMode.WRITE], "test_token", 1234567890
    )

    asyncio.run(
        connection._send_messages(  # pylint: disable=protected-access
            [
                Message(
                    id="1",
                    message="Hi @alice.bsky.social!",
                    source_connection="bluesky",
                    metadata=MessageMetadata(
                        mentions=[
                            MessageMention(
                                url="https://bsky.app/profile/did:plc:alice",
                                username="@alice.bsky.social",
                            ),
                        ],
                    ),
                ),
            ]
        )
    )

    discord_client.fetch_channel.return_value.send.assert_awaited_once_with(
        "Hi [@alice.bsky.social](https://bsky.app/profile/did:plc:alice)!"
    )
