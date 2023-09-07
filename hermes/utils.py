"""
Utility functions for the Hermes package.
"""

from time import sleep
from typing import Any, Callable


def wrap_while_true(
    callback: Callable[[], Any], sleep_interval: int
) -> Callable[[], Any]:
    """
    Wrap a function to be called within a `while True` scope,
    sleeping for a given interval between calls.
    """

    def wrapper() -> None:
        while True:
            callback()
            sleep(sleep_interval)

    return wrapper
