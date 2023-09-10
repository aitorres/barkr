"""
Module to implement a generic, wrapper model for messages.

A message is a generic object that can be posted to a social media network
OR retrieved from a social media network, with an ID and a message body, as
well as (potentially) other metadata that each connection can decide
whether or not to take into account.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    """
    A generic message object with an ID and a message body,
    as well as (potentially) other metadata that each connection
    can decide whether or not to take into account.
    """

    id: str
    message: str
