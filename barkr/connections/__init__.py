"""
Re-exporting all connection classes and enums from the connections submodules
for ease of use.

You can refer to each submodule for more information about the classes and enums,
and how to use them.
"""

from barkr.connections.base import Connection, ConnectionMode
from barkr.connections.bluesky import BlueskyConnection
from barkr.connections.discord import DiscordConnection
from barkr.connections.mastodon import MastodonConnection
from barkr.connections.mastodon_activity_bot import MastodonActivityBotConnection
from barkr.connections.rss import RSSConnection
from barkr.connections.telegram import TelegramConnection
from barkr.connections.twitter import TwitterConnection

__all__ = [
    "Connection",
    "TwitterConnection",
    "MastodonActivityBotConnection",
    "MastodonConnection",
    "ConnectionMode",
    "DiscordConnection",
    "BlueskyConnection",
    "TelegramConnection",
    "RSSConnection",
]
