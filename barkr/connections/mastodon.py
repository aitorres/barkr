"""
Module to implement a custom connection class for Mastodon instances,
supporting reading and writing statuses from the authenticated user
via their access token.
"""

import logging
import mimetypes
from typing import Any, Final, Optional

import requests
from bs4 import BeautifulSoup
from mastodon import Mastodon
from mastodon.errors import MastodonNetworkError
from mastodon.return_types import MediaAttachment, Status

from barkr.connections.base import Connection, ConnectionMode
from barkr.models import Media, Message, MessageType
from barkr.models.message import MessageVisibility
from barkr.utils import REQUESTS_EMBED_GET_TIMEOUT, REQUESTS_HEADERS

logger = logging.getLogger()

MASTODON_WRITE_RETRIES: Final[int] = 3


class MastodonConnection(Connection):
    """
    Custom connection class for Mastodon instances,
    supporting reading and writing statuses from the authenticated user.
    """

    supported_message_type = MessageType.TEXT_MEDIA

    service: Mastodon
    min_id: Optional[str]

    def __init__(
        self,
        name: str,
        modes: list[ConnectionMode],
        access_token: str,
        instance_url: str,
    ) -> None:
        """
        Initializes the connection with a name and a list of modes
        as well as the access token and instance URL.

        Validates the access token and instance URL by attempting to
        verify the credentials of the authenticated user and retrieve
        the account ID.

        :param name: The name of the connection
        :param modes: A list of modes for the connection
        :param access_token: The access token for the authenticated user
        :param instance_url: The URL of the Mastodon instance
        """
        super().__init__(name, modes)

        logger.info(
            "Initializing Mastodon (%s) connection to instance %s",
            self.name,
            instance_url,
        )
        self.service = Mastodon(
            access_token=access_token,
            api_base_url=instance_url,
            request_timeout=10,
        )
        self.account_id: str = self.service.account_verify_credentials()["id"]
        logger.info(
            "Mastodon (%s) connection initialized! (Account ID: %s)",
            self.name,
            self.account_id,
        )

        current_statuses = self.service.account_statuses(
            self.account_id, exclude_reblogs=True, exclude_replies=True
        )
        if current_statuses:
            self.min_id = current_statuses[0]["id"]
            logger.info("Mastodon (%s) initial min_id: %s", self.name, self.min_id)
        else:
            self.min_id = None
            logger.info("Mastodon (%s) initial min_id not set.", self.name)

    def _fetch(self) -> list[Message]:
        """
        Fetch messages from this connection

        :return: A list of messages
        """

        statuses: list[Status] = self.service.account_statuses(
            self.account_id,
            exclude_reblogs=True,
            exclude_replies=True,
            min_id=self.min_id,
        )

        if statuses:
            logger.info(
                "Fetched %s new statuses from Mastodon (%s)", len(statuses), self.name
            )
            self.min_id = statuses[0]["id"]
        else:
            logger.info("No new statuses fetched from Mastodon (%s)", self.name)

        return [
            Message(
                id=status["id"],
                message=BeautifulSoup(status["content"], "lxml").text,
                language=status["language"],
                label=status["spoiler_text"] or None,
                visibility=MessageVisibility.from_mastodon_visibility(
                    status["visibility"]
                ),
                media=_get_media_list_from_status(status),
            )
            for status in statuses
            if status["in_reply_to_id"] is None and status["reblog"] is None
        ]

    def _post(self, messages: list[Message]) -> list[str]:
        """
        Post messages from a list to the Mastodon instance

        :param messages: A list of messages to be posted
        :return: A list of message IDs
        """

        posted_message_ids: list[str] = []

        for message in messages:
            attempts = 0

            media_list = _post_media_list_to_mastodon(self.service, message.media)

            while attempts < MASTODON_WRITE_RETRIES:
                try:
                    posted_message = self.service.status_post(
                        message.message,
                        language=message.language,
                        spoiler_text=message.label or "",
                        visibility=message.visibility.to_mastodon_visibility(),
                        media_ids=media_list,
                    )
                except MastodonNetworkError as e:
                    if attempts < MASTODON_WRITE_RETRIES - 1:
                        logger.warning(
                            "Mastodon network error posting status to "
                            "Mastodon (%s), will retry. Error: %s",
                            self.name,
                            e,
                        )
                        attempts += 1
                    else:
                        logger.error(
                            "Failed to post status to Mastodon (%s) "
                            "after %s attempts: %s",
                            self.name,
                            MASTODON_WRITE_RETRIES,
                            e,
                        )
                        raise
                else:
                    break

            posted_message_ids.append(posted_message["id"])
            logger.info(
                "Posted status to Mastodon (%s): %s", self.name, message.message
            )

        return posted_message_ids


def _post_media_list_to_mastodon(
    service: Mastodon, media_list: list[Media]
) -> list[MediaAttachment]:
    """
    Helper function to post a list of Media objects to Mastodon.

    :param media_list: A list of Media objects
    :return: A list of MediaAttachment objects
    """

    media_attachments: list[MediaAttachment] = []

    for media in media_list:
        if not media.is_valid():
            logger.warning("Invalid media object, skipping posting to Mastodon")
            continue

        # Uploading the media to Mastodon
        try:
            media_attachment = service.media_post(
                media_file=media.content,
                mime_type=media.mime_type,
                description=media.alt_text,
            )
        except MastodonNetworkError as e:
            logger.error("Failed to upload media: %s", e)
            continue

        media_attachments.append(media_attachment)

    return media_attachments


def _get_media_list_from_status(status: dict[str, Any]) -> list[Media]:
    """
    Helper function to extract Media object instances from
    a Mastodon status, if they exist.

    :param status: The Mastodon status object
    :return: A list of Media objects
    """

    media_list: list[Media] = []

    for media_attachment in status["media_attachments"]:
        media_type = media_attachment["type"]

        if media_type not in ["image", "video"]:
            logger.warning(
                "Unsupported media type %s in status %s",
                media_type,
                status["id"],
            )
            continue

        url = media_attachment["url"]

        # Downloading the content of the media from its URL
        try:
            response = requests.get(
                url, timeout=REQUESTS_EMBED_GET_TIMEOUT, headers=REQUESTS_HEADERS
            )
        except MastodonNetworkError as e:
            logger.error("Failed to download media from %s: %s", url, e)
            continue

        if response.status_code == 200:
            media_content = response.content

            # Guessing the MIME type from the URL
            mime_type, _ = mimetypes.guess_type(url)

            if mime_type is None:
                logger.warning(
                    "Could not determine MIME type for media from URL %s", url
                )
                continue

            alt_text = media_attachment["description"] or ""
            media = Media(
                mime_type=mime_type,
                content=media_content,
                alt_text=alt_text,
            )

            if media.is_valid():
                media_list.append(media)

    return media_list
