"""
Module to implement a custom connection class for Bluesky accounts,
supporting reading and writing statuses from the authenticated user
via their handle and password.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Final, Optional, Union
from urllib.parse import urlparse

import requests
from atproto import Client
from atproto_client.exceptions import BadRequestError, InvokeTimeoutError  # type: ignore
from atproto_client.models import (  # type: ignore
    AppBskyEmbedExternal,
    AppBskyEmbedImages,
    AppBskyEmbedRecord,
    AppBskyEmbedRecordWithMedia,
    AppBskyEmbedVideo,
    AppBskyRichtextFacet,
)
from atproto_client.models.blob_ref import BlobRef  # type: ignore
from atproto_client.models.common import XrpcError  # type: ignore
from bs4 import BeautifulSoup, Tag

from barkr.connections.base import Connection, ConnectionMode
from barkr.models import Message
from barkr.utils import (
    REQUESTS_EMBED_GET_TIMEOUT,
    REQUESTS_HEADERS,
    extract_urls_from_text,
)

logger = logging.getLogger()

BLUESKY_MAX_MESSAGE_LENGTH: Final[int] = 300


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

                    language = None
                    if record.langs:
                        language = record.langs[0]

                    messages.append(
                        Message(id=post.indexed_at, message=text, language=language)
                    )

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
            if len(message.message) > BLUESKY_MAX_MESSAGE_LENGTH:
                logger.warning(
                    "Message length exceeds Bluesky (%s) "
                    "maximum length (%s), skipping: %s",
                    self.name,
                    BLUESKY_MAX_MESSAGE_LENGTH,
                    message.message,
                )
                continue

            embed, facets = self._generate_post_embed_and_facets(message.message)
            language = [message.language] if message.language else None
            try:
                created_record = self.service.send_post(
                    text=message.message,
                    embed=embed,
                    facets=facets if facets else None,
                    langs=language,
                )
            except InvokeTimeoutError as e:
                # Something happened with the Bluesky API, let's recover
                logger.error(
                    "Bluesky (%s) post failed with timeout error: %s", self.name, e
                )

                # In case we _did_ post the message, we don't want to
                # re-post it again
                self.min_id = _get_current_indexed_at()
                continue
            except BadRequestError as e:
                # We could be trying to create an embed that is too large,
                # let's recover
                error_response = e.response
                content = error_response.content

                if isinstance(content, XrpcError) and content.error == "BlobTooLarge":
                    logger.warning(
                        "Bluesky (%s) post failed due to embed size, "
                        "reattempting post without embed.",
                        self.name,
                    )
                    created_record = self.service.send_post(
                        text=message.message,
                        embed=None,
                        facets=facets if facets else None,
                        langs=language,
                    )
                else:
                    logger.error(
                        "Bluesky (%s) post failed with unexpected error: %s",
                        self.name,
                        content,
                    )
                    raise e

            created_uri = created_record.uri

            # NOTE: introducing an artificial delay to ensure the post is indexed
            # before fetching the post details
            time.sleep(2)

            try:
                post_details = self.service.get_posts([created_uri]).posts[0]
                indexed_at = post_details.indexed_at
            except IndexError:
                indexed_at = _get_current_indexed_at()
                logger.error(
                    "Failed to fetch post details for Bluesky (%s) post: %s, "
                    "manually setting indexed_at to %s",
                    self.name,
                    created_uri,
                    indexed_at,
                )

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

        embed = None
        facets: list[AppBskyRichtextFacet.Main] = []

        for url in extract_urls_from_text(text):
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
                    if (
                        meta_description := _get_meta_tag_from_html_metadata(
                            soup, "og:description"
                        )
                    ) is not None:
                        description = meta_description

                    # Extract the image from the meta tag
                    if (
                        image := _get_meta_tag_from_html_metadata(soup, "og:image")
                    ) is not None:
                        # Fetching the image and reuploading to Bluesky
                        thumbnail_blob = self._upload_image_url_to_atproto_blob(image)

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
                url_index = text.index(url)
                facets.append(
                    AppBskyRichtextFacet.Main(
                        features=[
                            AppBskyRichtextFacet.Link(
                                uri=url,
                            )
                        ],
                        index=AppBskyRichtextFacet.ByteSlice(
                            byte_start=len(text[:url_index].encode("utf-8")),
                            byte_end=len(text[: url_index + len(url)].encode("utf-8")),
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

    def _upload_image_url_to_atproto_blob(self, image_url: str) -> Optional[BlobRef]:
        """
        Given a URL to an image, fetches the image and uploads it
        to Bluesky as a blob.

        :param image_url: The URL of the image to upload
        :return: The BlobRef object referencing the uploaded image blob
        """

        try:
            img_data = requests.get(
                image_url,
                timeout=REQUESTS_EMBED_GET_TIMEOUT,
                headers=REQUESTS_HEADERS,
            ).content
        except requests.RequestException as e:
            logger.warning("Failed to fetch image from %s: %s", image_url, e)
            return None

        try:
            return self.service.upload_blob(img_data).blob
        except (InvokeTimeoutError, BadRequestError) as e:
            logger.warning("Failed to upload image to Bluesky (%s): %s", self.name, e)
            return None


def _get_meta_tag_from_html_metadata(
    soup: BeautifulSoup, tag_name: str
) -> Optional[str]:
    """
    Extracts the content of meta tag from the HTML metadata of a page.

    If there are multiple meta tags with the same property,
    only the first one is returned.

    :param soup: The BeautifulSoup object containing the HTML metadata
    :param tag_name: The name of the meta tag to extract
    :return: The meta tag content if found, otherwise None
    """

    tag = soup.find("meta", attrs={"property": tag_name})
    if isinstance(tag, Tag) and tag.has_attr("content"):
        tag_content = tag["content"]

        if isinstance(tag_content, list):
            tag_content = tag_content[0]

        return tag_content

    return None


def _get_current_indexed_at() -> str:
    """
    Returns the current UTC timestamp in ISO format,
    to mock the Bluesky API's indexed_at field
    right after posting a message if the post details cannot be fetched.

    :return: The current indexed_at timestamp
    """

    return datetime.now(timezone.utc).isoformat()
