"""
Re-exporting all connection classes and enums from the connections submodules
for ease of use.

You can refer to each submodule for more information about the classes and enums,
and how to use them.

Connection subclasses are imported lazily (PEP 562 module `__getattr__`) so that
importing this package does not eagerly load  third-party SDKs until required.
"""

import importlib
from typing import TYPE_CHECKING, Any

from barkr.connections.base import Connection, ConnectionMode, ThreadAwareConnection

if TYPE_CHECKING:
    from barkr.connections.bluesky import BlueskyConnection
    from barkr.connections.discord import DiscordConnection
    from barkr.connections.mastodon import MastodonConnection
    from barkr.connections.mastodon_activity_bot import MastodonActivityBotConnection
    from barkr.connections.rss import RSSConnection
    from barkr.connections.telegram import TelegramConnection
    from barkr.connections.twitter import TwitterConnection
    from barkr.connections.webhook import WebhookConnection

__all__ = [
    "Connection",
    "ThreadAwareConnection",
    "TwitterConnection",
    "MastodonActivityBotConnection",
    "MastodonConnection",
    "ConnectionMode",
    "DiscordConnection",
    "BlueskyConnection",
    "TelegramConnection",
    "RSSConnection",
    "WebhookConnection",
]

_LAZY_CONNECTIONS: dict[str, str] = {
    "BlueskyConnection": "barkr.connections.bluesky",
    "DiscordConnection": "barkr.connections.discord",
    "MastodonConnection": "barkr.connections.mastodon",
    "MastodonActivityBotConnection": "barkr.connections.mastodon_activity_bot",
    "RSSConnection": "barkr.connections.rss",
    "TelegramConnection": "barkr.connections.telegram",
    "TwitterConnection": "barkr.connections.twitter",
    "WebhookConnection": "barkr.connections.webhook",
}


def __getattr__(name: str) -> Any:
    """
    Lazily import and cache a connection class on first attribute access.

    :param name: The attribute being accessed on this package
    :return: The requested connection class
    :raises AttributeError: If the attribute is not a known connection class
    """

    module_path = _LAZY_CONNECTIONS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    attribute = getattr(importlib.import_module(module_path), name)
    globals()[name] = attribute
    return attribute


def __dir__() -> list[str]:
    """
    Include lazily-exported connection classes in `dir()` output.
    """

    return sorted(__all__)
