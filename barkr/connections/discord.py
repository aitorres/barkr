"""
Module to implement a custom connection class for Discord,
supporting writing messages to a Discord channel
via a Discord bot.

This module uses the discord.py library to interact
with the Discord API.
"""

import asyncio
import logging

import discord

from barkr.connections.base import Connection, ConnectionMode
from barkr.models import Message

logger = logging.getLogger()


class DiscordConnection(Connection):
    """
    Custom connection class for Discord,
    supporting writing messages to a Discord channel
    via a Discord bot.
    """

    intents: discord.Intents
    token: str
    channel_id: int

    def __init__(
        self, name: str, modes: list[ConnectionMode], token: str, channel_id: int
    ) -> None:
        """
        Initializes the connection with a name and a list of modes, as well
        as the Discord bot token and channel ID.

        The Discord bot must be set up beforehand and be added to the server
        where messages will be posted, with visibility and permissions set
        to view and send messages in the desired channel.

        "Message Content Intent" must be enabled in the Discord Developer Portal
        for the bot to be able to read message content.

        Since Discord.py is usually a blocking library and `barkr` is not
        designed to have connections blocking the main thread, we don't
        create a client on initialization. Instead, we create the client
        as needed to post messages. This might add some overhead,
        but it allows us to keep the main thread free from blocking.

        NOTE: only the write mode is supported. Attempting to use read
        mode will raise a NotImplementedError.

        :param name: The name of the connection
        :param modes: A list of modes for the connection
        :param token: The token for the Discord bot
        """
        super().__init__(name, modes)

        logger.info("Initializing Discord (%s) connection", self.name)
        if self.modes != [ConnectionMode.WRITE]:
            raise NotImplementedError("DiscordConnection only supports write mode.")

        self.intents = discord.Intents.default()
        self.intents.message_content = True

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
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._send_messages(messages))
        logger.info("Finished posting messages to Discord (%s)", self.name)

        return []

    async def _send_messages(self, messages: list[Message]) -> None:
        """
        Send a list of messages to a Discord channel as the authenticated bot.

        Creates a new Discord client, authenticates the bot with the provided token,
        and sends messages to the specified channel without blocking the main thread.

        :param messages: A list of messages to send
        """

        client = discord.Client(intents=self.intents)

        @client.event
        async def on_ready():
            logger.info(
                "Discord client connected successfully to send %s messages",
                len(messages),
            )
            channel = client.get_channel(self.channel_id)
            for message in messages:
                await channel.send(message.message)
                logger.info("Message posted to Discord (%s) channel", self.name)

            await client.close()

        await client.start(self.token)
