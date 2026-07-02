"""
Module to implement unit tests for the Discord connection class
"""

import asyncio
from typing import Any, Optional

import pytest

from barkr.connections import ConnectionMode, DiscordConnection
from barkr.models import Message
from barkr.models.message_mention import MessageMention
from barkr.models.message_metadata import MessageMetadata


class MockDiscordChannel:
    """Mock Discord channel collecting sent messages."""

    sent_messages: list[str] = []

    @classmethod
    def reset(cls) -> None:
        """Reset shared test state."""
        cls.sent_messages = []

    async def send(self, message: str) -> None:
        """Record the outbound Discord message."""
        self.sent_messages.append(message)


class MockDiscordClient:
    """Mock Discord client with minimal lifecycle hooks."""

    started_tokens: list[str] = []
    requested_channels: list[int] = []
    close_calls = 0

    def __init__(self, *, intents: Any) -> None:
        self.intents = intents
        self._on_ready: Optional[Any] = None

    @classmethod
    def reset(cls) -> None:
        """Reset shared test state."""
        cls.started_tokens = []
        cls.requested_channels = []
        cls.close_calls = 0

    def event(self, callback: Any) -> Any:
        """Store the registered ready callback."""
        self._on_ready = callback
        return callback

    def get_channel(self, channel_id: int) -> MockDiscordChannel:
        """Return a mock channel and record the request."""
        self.requested_channels.append(channel_id)
        return MockDiscordChannel()

    async def close(self) -> None:
        """Record the close lifecycle event."""
        type(self).close_calls += 1

    async def start(self, token: str) -> None:
        """Record the start token and trigger on_ready immediately."""
        self.started_tokens.append(token)
        assert self._on_ready is not None
        await self._on_ready()


class MockEventLoop:
    """Mock event loop that executes the coroutine immediately."""

    run_until_complete_calls = 0

    @classmethod
    def reset(cls) -> None:
        """Reset shared test state."""
        cls.run_until_complete_calls = 0

    def run_until_complete(self, coroutine: Any) -> None:
        """Run the awaited coroutine inline for the test."""
        type(self).run_until_complete_calls += 1
        asyncio.run(coroutine)


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


def test_discord_send_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    """Send messages through the mocked Discord client lifecycle."""

    MockDiscordChannel.reset()
    MockDiscordClient.reset()

    monkeypatch.setattr("discord.Client", MockDiscordClient)

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

    assert MockDiscordClient.started_tokens == ["test_token"]
    assert MockDiscordClient.requested_channels == [1234567890]
    assert MockDiscordChannel.sent_messages == ["hello", "world"]
    assert MockDiscordClient.close_calls == 1


def test_discord_post_uses_event_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Create an event loop and drive the async sender through _post."""

    received_messages: list[list[Message]] = []

    MockEventLoop.reset()

    async def mock_send_messages(_, messages: list[Message]) -> None:
        received_messages.append(messages)

    monkeypatch.setattr("asyncio.new_event_loop", MockEventLoop)
    monkeypatch.setattr(
        DiscordConnection,
        "_send_messages",
        mock_send_messages,
    )

    connection = DiscordConnection(
        "Discord Connection", [ConnectionMode.WRITE], "test_token", 1234567890
    )
    messages = [Message("1", "hello", "source")]

    assert not connection._post(messages)  # pylint: disable=protected-access
    assert MockEventLoop.run_until_complete_calls == 1
    assert received_messages == [messages]


def test_discord_renders_mentions_with_profile_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mention metadata is rendered as markdown links on Discord."""

    MockDiscordChannel.reset()
    MockDiscordClient.reset()

    monkeypatch.setattr("discord.Client", MockDiscordClient)

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

    assert MockDiscordChannel.sent_messages == [
        "Hi [@alice.bsky.social](https://bsky.app/profile/did:plc:alice)!"
    ]
