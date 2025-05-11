"""
Module to implement generic enums and models to represent
message types.
"""

from enum import Enum


class MessageType(Enum):
    """
    Enum to represent the type of messages a connection supports
    """

    TEXT_ONLY = 1
    TEXT_MEDIA = 2
