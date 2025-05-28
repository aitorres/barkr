"""
Utility functions for the Barkr package.
"""

import re
from time import sleep
from typing import Any, Callable, Final

REQUESTS_EMBED_GET_TIMEOUT: Final[int] = 3

REQUESTS_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) " "Gecko/20100101 Firefox/20.0"
    )
}

URL_REGEX_PATTERN: Final[re.Pattern[str]] = re.compile(r"http[s]?://[^\s]+")


def wrap_while_true(
    callback: Callable[[], Any], sleep_interval: int
) -> Callable[[], Any]:
    """
    Wrap a function to be called within a `while True` scope,
    sleeping for a given interval between calls.

    :param callback: The function to be called within the loop
    :param sleep_interval: The interval to sleep between calls, in seconds
    :return: The wrapped function
    """

    def wrapper() -> None:
        while True:
            callback()
            sleep(sleep_interval)

    return wrapper


def extract_urls_from_text(text: str) -> list[str]:
    """
    Given a text string, extract and return all URLs
    found within it in a list.

    URLs are not validated as reachable and no connection
    is made to them, extraction is done using regex.

    :param text: The text to extract URLs from
    :return: A list of extracted URLs
    """

    return URL_REGEX_PATTERN.findall(text)
