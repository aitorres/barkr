"""
Utility functions for the Barkr package.
"""

import re
from time import sleep
from typing import Any, Callable


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

    return re.findall(r"http[s]?://[^\s]+", text)
