"""
Module to implement a custom connection class for ActivityBot,
an ActivityPub bot for Mastodon.

Supports writing statuses to Mastodon from the bot via
their API url and password.

ref: https://gitlab.com/edent/activity-bot
"""

import logging
import mimetypes
from typing import Optional

import requests

from barkr.connections.base import Connection, ConnectionMode
from barkr.models import Media, Message, MessageType
from barkr.utils import REQUESTS_EMBED_GET_TIMEOUT, REQUESTS_HEADERS

logger = logging.getLogger()


class MastodonActivityBotConnection(Connection):
    """
    Custom connection class for ActivityBot, an ActivityPub bot for Mastodon.

    Supports writing statuses to Mastodon from the bot via
    their API url and password.
    """

    __slots__ = ("password", "api_url")

    password: str
    api_url: str

    def __init__(
        self, name: str, modes: list[ConnectionMode], api_url: str, password: str
    ) -> None:
        """
        Initializes the connection with a name, API URL, and password.

        :param name: The name of the connection
        :param modes: A list of modes for the connection
        :param api_url: The API URL for the ActivityBot send action
        :param password: The password for the ActivityBot
        """
        super().__init__(name, modes)
        self.supported_message_type = MessageType.TEXT_MEDIA

        logger.info("Initializing MastodonActivityBot (%s) connection", self.name)
        if self.modes != [ConnectionMode.WRITE]:
            raise NotImplementedError(
                "MastodonActivityBotConnection only supports write mode."
            )

        self.api_url = api_url
        self.password = password

        logger.info(
            "MastodonActivityBot (%s) connection initialized! (API URL: %s)",
            self.name,
            self.api_url,
        )

    def _post(self, messages: list[Message]) -> list[str]:
        """
        Posts the given messages to ActivityPub via
        the ActivityBot send action.

        :param messages: The list of messages to post
        :return: A list of message IDs (empty for ActivityBot)
        """

        for message in messages:
            logger.info(
                "Posting message to ActivityBot (%s): %s", self.name, message.message
            )

            data: dict[str, str] = {
                "password": self.password,
                "content": message.message,
            }
            files: Optional[dict[str, tuple[str, bytes, str]]] = None

            image = self._select_image_attachment(message)
            if image is not None:
                extension = mimetypes.guess_extension(image.mime_type) or ".bin"
                filename = f"upload{extension}"
                files = {"image": (filename, image.content, image.mime_type)}
                if image.alt_text:
                    data["alt"] = image.alt_text

            response = requests.post(
                self.api_url,
                data=data,
                files=files,
                headers=REQUESTS_HEADERS,
                timeout=REQUESTS_EMBED_GET_TIMEOUT,
            )

            if not response.ok:
                logger.error(
                    "Failed to post message to ActivityBot (%s): %s",
                    self.name,
                    response.text,
                )
            else:
                logger.info(
                    "Successfully posted message to ActivityBot (%s) with response: %s",
                    self.name,
                    response.text,
                )

        return []

    def _select_image_attachment(self, message: Message) -> Optional[Media]:
        """
        Pick the first valid image attachment from the message, if any.

        The ActivityBot `send` endpoint accepts a single `image` file upload
        plus an optional `alt` text field, so any additional images (or any videos)
        are skipped with a warning.

        :param message: The message whose media attachments to inspect
        :return: The first valid image `Media`, or `None` if there is none
        """

        first_image: Optional[Media] = next(
            (
                media
                for media in message.media
                if media.is_valid() and media.mime_type.startswith("image/")
            ),
            None,
        )

        if len(message.media) > 1:
            logger.warning(
                "ActivityBot (%s) only supports a single image per post;"
                " %d additional media attachment(s) will be skipped.",
                self.name,
                len(message.media) - 1,
            )

        return first_image
