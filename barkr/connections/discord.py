"""
Module to implement a custom connection class for Discord,
supporting writing messages to a Discord channel
via a Discord bot.

This module uses the discord.py library to interact
with the Discord API.
"""

import asyncio
import logging
from typing import Optional

import discord

from barkr.connections.base import Connection, ConnectionMode
from barkr.models import MentionStyle, Message

logger = logging.getLogger()


class DiscordConnection(Connection):
    """
    Custom connection class for Discord,
    supporting writing messages to a Discord channel
    via a Discord bot.
    """

    __slots__ = ("intents", "token", "channel_id")

    intents: discord.Intents
    token: str
    channel_id: int

    def __init__(
        self,
        name: str,
        modes: list[ConnectionMode],
        token: str,
        channel_id: int,
        group: Optional[str] = None,
    ) -> None:
        """
        Initializes the connection with a name and a list of modes, as well
        as the Discord bot token and channel ID.

        The Discord bot must be set up beforehand and be added to the server
        where messages will be posted, with visibility and permissions set
        to view and send messages in the desired channel.

        Each batch uses a short-lived client to send messages through the HTTP API.

        NOTE: only the write mode is supported. Attempting to use read
        mode will raise a NotImplementedError.

        :param name: The name of the connection
        :param modes: A list of modes for the connection
        :param token: The token for the Discord bot
        :param group: (optional) The routing group for the connection
        """
        super().__init__(name, modes, group)

        logger.info("Initializing Discord (%s) connection", self.name)
        if self.modes != [ConnectionMode.WRITE]:
            raise NotImplementedError("DiscordConnection only supports write mode.")

        self.intents = discord.Intents.default()

        self.token = token
        self.channel_id = channel_id

        logger.info("Discord (%s) connection initialized successfully", self.name)

    def _post(self, messages: list[Message]) -> list[str]:
        """
        Post a list of messages to a Discord channel as the authenticated bot.

        :param messages: A list of messages to post
        """

        logger.info(
            "Starting new event loop to send messages to Discord (%s)", self.name
        )
        asyncio.run(self._send_messages(messages))
        logger.info("Finished posting messages to Discord (%s)", self.name)

        return []

    async def _send_messages(self, messages: list[Message]) -> None:
        """
        Send a list of messages to a Discord channel as the authenticated bot.

        Authenticates a short-lived client and sends directly through the HTTP API.
        Errors propagate to the caller, and the client closes on every exit path.

        :param messages: A list of messages to send
        """

        async with discord.Client(intents=self.intents) as client:
            await client.login(self.token)
            channel = await client.fetch_channel(self.channel_id)
            if not isinstance(channel, discord.abc.Messageable):
                raise TypeError(
                    f"Discord channel {self.channel_id} does not support messages."
                )

            logger.info(
                "Discord client connected successfully to send %s messages",
                len(messages),
            )
            for message in messages:
                await channel.send(message.get_content(MentionStyle.MARKDOWN_LINK))
                logger.info("Message posted to Discord (%s) channel", self.name)
