"""
Module to implement a custom connection class for Bluesky accounts,
supporting reading and writing statuses from the authenticated user
via their handle and password.
"""

import logging
import re
import time
from datetime import datetime
from typing import Final, Optional, Union
from urllib.parse import urlparse

import requests
from atproto import Client
from atproto_client.models import (  # type: ignore
    AppBskyEmbedExternal,
    AppBskyEmbedImages,
    AppBskyEmbedRecord,
    AppBskyEmbedRecordWithMedia,
    AppBskyEmbedVideo,
    AppBskyRichtextFacet,
)
from bs4 import BeautifulSoup, Tag

from barkr.connections.base import Connection, ConnectionMode
from barkr.models.message import Message

logger = logging.getLogger()

REQUESTS_EMBED_GET_TIMEOUT: Final[int] = 3
REQUESTS_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) " "Gecko/20100101 Firefox/20.0"
    )
}


class BlueskyConnection(Connection):
    """
    Custom connection class for Bluesky accounts,
    supporting reading and writing statuses from the authenticated user.

    Requires handle and an app password for authentication.
    """

    def __init__(
        self, name: str, modes: list[ConnectionMode], handle: str, password: str
    ) -> None:
        """
        Initializes the connection with a name and a list of modes
        and sets up the initial connection between the client and Bluesky
        for the given user.

        NOTE: it is recommended to use an app password instead of the user's password.
        ref: https://bsky.app/settings/app-passwords

        :param name: The name of the connection
        :param modes: A list of modes for the connection
        :param handle: The handle of the authenticated user
        :param password: The app password of the authenticated user
        """

        super().__init__(name, modes)

        logger.info(
            "Initializing Bluesky (%s) connection for user %s",
            self.name,
            handle,
        )

        self.service = Client()
        self.service.login(handle, password)
        self.handle: str = handle

        logger.info(
            "Bluesky (%s) connection initialized! (User handle: %s)",
            self.name,
            self.handle,
        )

        user_feed = self.service.app.bsky.feed.get_author_feed({"actor": handle}).feed
        if user_feed:
            # Set the initial min_id to the most recent post's indexed_at,
            # which is a UTC timestamp string
            self.min_id: Optional[str] = user_feed[0].post.indexed_at
            logger.info("Bluesky (%s) initial min_id: %s", self.name, self.min_id)
        else:
            self.min_id = None
            logger.info("Bluesky (%s) initial min_id not set.", self.name)

    def _fetch(self) -> list[Message]:
        """
        Fetches messages from the authenticated user's account.

        :return: A list of messages
        """

        messages: list[Message] = []

        user_feed = self.service.app.bsky.feed.get_author_feed(
            {"actor": self.handle}
        ).feed
        if user_feed:
            for feed_view in user_feed:
                post = feed_view.post

                # Ignoring reposts
                if post.viewer is not None and post.viewer.repost is not None:
                    continue

                # Ignoring replies
                if post.record.reply is not None:
                    continue

                if self.min_id is None or datetime.fromisoformat(
                    post.indexed_at
                ) > datetime.fromisoformat(self.min_id):
                    record = post.record
                    if (embed := record.embed) is not None:
                        text = self._process_text_with_embed(record.text, embed)
                    else:
                        text = record.text

                    messages.append(Message(id=post.indexed_at, message=text))

        if messages:
            self.min_id = messages[0].id
            logger.info("Bluesky (%s) has %s new messages.", self.name, len(messages))
        else:
            logger.info("Bluesky (%s) has no new messages.", self.name)

        return messages

    def _post(self, messages: list[Message]) -> list[str]:
        """
        Posts the given messages to the authenticated user's account.

        :param messages: The messages to post
        :return: A list of IDs of the posted messages
        """

        posted_message_ids: list[str] = []

        for message in messages:
            embed, facets = self._generate_post_embed_and_facets(message.message)
            created_record = self.service.send_post(
                text=message.message, embed=embed, facets=facets if facets else None
            )
            created_uri = created_record.uri

            # NOTE: introducing an artificial delay to ensure the post is indexed
            # before fetching the post details
            time.sleep(1)

            post_details = self.service.get_posts([created_uri]).posts[0]
            indexed_at = post_details.indexed_at

            logger.info(
                "Posted message %s to Bluesky (%s) connection (URI: %s, Indexed At: %s)",
                message.message,
                self.name,
                created_uri,
                indexed_at,
            )

            self.min_id = indexed_at
            posted_message_ids.append(indexed_at)

        return posted_message_ids

    def _generate_post_embed_and_facets(
        self, text: str
    ) -> tuple[Optional[AppBskyEmbedExternal.Main], list[AppBskyRichtextFacet.Main]]:
        """
        If a link is present on the text for a post to be created,
        creates an Embed object for the link.

        This allows Bluesky to display the link as a preview.

        Also generate facets for the link to be used in the post.

        :param text: The text of the post
        :return: A tuple containing the Embed object and a list of facets
        """

        # Extract the first link from the text
        urls = re.findall(r"http[s]?://[^\s]+", text)

        embed = None
        facets: list[AppBskyRichtextFacet.Main] = []

        for url in urls:
            # Hit the URL to check if it is valid and extract title and description
            try:
                # Using a very short timeout, we don't want to spend too much time here
                response = requests.get(
                    url, timeout=REQUESTS_EMBED_GET_TIMEOUT, headers=REQUESTS_HEADERS
                )
            except requests.RequestException:
                continue

            if response.status_code == 200:
                if embed is None:
                    # Parse the response to extract title, description and image
                    soup = BeautifulSoup(response.content, "html.parser")
                    title = soup.title.string if soup.title else urlparse(url).netloc
                    description = url
                    thumbnail_blob = None

                    # Extract the description from the meta tag
                    parsed_description = soup.find(
                        "meta", attrs={"name": "description"}
                    )
                    if isinstance(parsed_description, Tag):
                        description = parsed_description["content"]

                    # Extract the image from the meta tag
                    og_image = soup.find("meta", attrs={"property": "og:image"})
                    if isinstance(og_image, Tag):
                        image = og_image["content"]

                        if isinstance(image, list):
                            image = image[0]

                        img_data = requests.get(
                            image,
                            timeout=REQUESTS_EMBED_GET_TIMEOUT,
                            headers=REQUESTS_HEADERS,
                        ).content
                        thumbnail_blob = self.service.upload_blob(img_data).blob

                    # Prepare the Embed object
                    embed = AppBskyEmbedExternal.Main(
                        external=AppBskyEmbedExternal.External(
                            uri=url,
                            title=title,
                            description=description,
                            thumb=thumbnail_blob,
                        )
                    )

                # Create a facet for the link
                facets.append(
                    AppBskyRichtextFacet.Main(
                        features=[
                            AppBskyRichtextFacet.Link(
                                uri=url,
                            )
                        ],
                        index=AppBskyRichtextFacet.ByteSlice(
                            byte_start=text.index(url),
                            byte_end=text.index(url) + len(url),
                        ),
                    )
                )

        return embed, facets

    def _process_text_with_embed(
        self,
        text: str,
        embed: Optional[
            Union[
                AppBskyEmbedExternal.Main,
                AppBskyEmbedRecord.Main,
                AppBskyEmbedImages.Main,
                AppBskyEmbedVideo.Main,
                AppBskyEmbedRecordWithMedia.Main,
            ]
        ],
    ) -> str:
        """
        Handles the special case where a Bluesky post contains a link to an embedded
        resources that is not fully rendered as part of the text.

        Leveraging the Embed object, reconstructs the text to include
        the full URL to the resource.

        For example, when posting the URL
        https://open.spotify.com/track/0ElVpg9XIswx3XWs6kUj6a?si=0015d86587524ef9
        the text is trimmed to open.spotify.com/track/0ElVpg... but the
        Embed object contains the full URL.

        :param text: The original text of the post
        :param embed: The Embed object containing the link
        :return: The reconstructed text with the full URL
        """

        if embed is None:
            return text

        # Depending on the type of embed, we get the URL
        # from the corresponding field
        if isinstance(embed, AppBskyEmbedExternal.Main):
            url = embed.external.uri
        else:
            return text

        # We now want to find the word in the text that is contained
        # in the URL, and we only care for the _longest_ word
        # if there are multiple matches
        matching_word = ""
        for word in text.split():
            if word.replace("...", "") in url:
                if len(word) > len(matching_word):
                    matching_word = word

        if not matching_word:
            return text

        return text.replace(matching_word, url)
