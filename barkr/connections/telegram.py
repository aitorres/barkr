"""
Module to implement a custom connection class for Telegram,
supporting writing messages to a Telegram chat (or channel).

This module uses the python-telegram-bot library to interact
with the Telegram API.
"""

import asyncio
import logging

from telegram.ext import Application, ApplicationBuilder

from barkr.connections.base import Connection, ConnectionMode
from barkr.models import Message

logger = logging.getLogger()


class TelegramConnection(Connection):
    """
    Custom connection class for Telegram,
    supporting writing messages from a Telegram
    bot to a chat or channel.
    """

    app: Application
    chat_id: str

    def __init__(
        self, name: str, modes: list[ConnectionMode], token: str, chat_id: str
    ) -> None:
        """
        Initializes the connection with a name and a list of modes
        as well as the Telegram bot token and the chat id.

        Authenticates the bot with the provided token.

        NOTE: only the write mode is supported. Attempting to use read
        mode will raise a NotImplementedError.

        :param name: The name of the connection
        :param modes: A list of modes for the connection
        :param token: The token for the Telegram bot
        :param chat_id: The chat id for the chat or channel
        """
        super().__init__(name, modes)

        logger.info("Initializing Telegram (%s) connection", self.name)
        if self.modes != [ConnectionMode.WRITE]:
            raise NotImplementedError("TelegramConnection only supports write mode.")

        self.app = ApplicationBuilder().token(token).build()
        self.chat_id = chat_id
        logger.info("Telegram (%s) connection initialized successfully", self.name)

    def _post(self, messages: list[Message]) -> list[str]:
        """
        Post a list of messages to a Telegram chat / channel
        as the authenticated bot.

        :param messages: A list of messages to post
        :return: A list of message IDs
        """

        for message in messages:
            asyncio.run(
                self.app.bot.send_message(chat_id=self.chat_id, text=message.message)
            )
            logger.info("Message posted to Telegram (%s) chat / channel", self.name)

        return []
