"""
Stateless helpers for the Bluesky connection class.
"""

from typing import Optional, Union

from atproto_client.models import (
    AppBskyEmbedExternal,
    AppBskyEmbedImages,
    AppBskyEmbedRecord,
    AppBskyEmbedRecordWithMedia,
    AppBskyEmbedVideo,
    AppBskyRichtextFacet,
)
from atproto_client.models.app.bsky.feed.defs import FeedViewPost
from atproto_client.models.app.bsky.feed.post import Record as PostRecord
from bs4 import BeautifulSoup, Tag

from barkr.models import MessageMention

BlueskyEmbed = Optional[
    Union[
        AppBskyEmbedExternal.Main,
        AppBskyEmbedRecord.Main,
        AppBskyEmbedImages.Main,
        AppBskyEmbedVideo.Main,
        AppBskyEmbedRecordWithMedia.Main,
    ]
]


def get_meta_tag_from_html_metadata(
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


def is_quote_embed(embed: BlueskyEmbed) -> bool:
    """
    Determines if a given Bluesky post embed represents a quote to
    another post. Useful to skip quote posts when fetching messages,
    as we might not have all the context to reconstruct the quoted post
    on other connections.

    :param embed: The embed object to check
    :return: True if the embed is a quote, False otherwise
    """

    if embed is None:
        return False

    return isinstance(
        embed, (AppBskyEmbedRecord.Main, AppBskyEmbedRecordWithMedia.Main)
    )


def process_text_with_embed(text: str, embed: BlueskyEmbed) -> str:
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


def get_latest_own_post_uri(
    user_feed: list[FeedViewPost],
) -> Optional[str]:
    """
    Returns the URI of the most recent non-repost post in the feed,
    or None if all items are reposts.

    Only non-repost URIs are safe for min_id comparison because they
    share the authenticated user's DID prefix, making lexicographic
    ordering equivalent to chronological ordering.
    """

    for feed_view in user_feed:
        post = feed_view.post
        if post.viewer is None or post.viewer.repost is None:
            return str(post.uri)

    return None


def extract_mention_facets(record: PostRecord) -> Optional[list[MessageMention]]:
    """
    Extract mention facets from a Bluesky post record by parsing
    `app.bsky.richtext.facet#mention` facets.

    Returns None if the record has no facets or no mention features,
    so the result can be passed through to MessageMetadata as-is.
    """

    if not record.facets:
        return None

    raw_text_bytes = record.text.encode("utf-8")
    mentions: list[MessageMention] = []
    for facet in record.facets:
        for feature in facet.features or []:
            if isinstance(feature, AppBskyRichtextFacet.Mention):
                username = raw_text_bytes[
                    facet.index.byte_start : facet.index.byte_end
                ].decode("utf-8", errors="replace")
                mentions.append(
                    MessageMention(
                        url=f"https://bsky.app/profile/{feature.did}",
                        username=username,
                    )
                )

    return mentions or None
