"""
Module to implement unit tests for the Mastodon connection class
"""

from typing import Any

import pytest

from barkr.connections.base import ConnectionMode
from barkr.connections.mastodon import MastodonConnection
from barkr.models.message import Message


def test_mastodon_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Basic unit tests for the MastodonConnection class
    """

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_verify_credentials",
        lambda _: {"id": "1234567890"},
    )

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [],
    )

    mastodon_no_initial_statuses = MastodonConnection(
        "MastodonClass",
        [ConnectionMode.READ, ConnectionMode.WRITE],
        "test_token",
        "https://example.com",
    )
    assert mastodon_no_initial_statuses.name == "MastodonClass"
    assert mastodon_no_initial_statuses.account_id == "1234567890"
    assert mastodon_no_initial_statuses.min_id is None

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [
            {
                "id": "987654321",
                "reblog": None,
                "in_reply_to_id": None,
            }
        ],
    )

    mastodon = MastodonConnection(
        "MastodonClass",
        [ConnectionMode.READ, ConnectionMode.WRITE],
        "test_token",
        "https://example.com",
    )

    assert mastodon.name == "MastodonClass"
    assert mastodon.account_id == "1234567890"
    assert mastodon.min_id == "987654321"

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [],
    )

    messages = mastodon.read()
    assert not messages

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [
            {
                "id": "11223344",
                "content": "test message 1",
                "reblog": None,
                "in_reply_to_id": None,
            },
            {
                "id": "55667788",
                "content": "test message 2",
                "reblog": None,
                "in_reply_to_id": None,
            },
        ],
    )

    messages = mastodon.read()

    assert messages == [
        Message(id="11223344", message="test message 1"),
        Message(id="55667788", message="test message 2"),
    ]
    assert mastodon.min_id == "11223344"

    posted_messages: list[str] = []

    def status_post_mockup(_, message: str) -> dict[str, Any]:
        posted_messages.append(message)

        return {"id": "12121212" if message == "test message 3" else "23232323"}

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.status_post", status_post_mockup
    )

    mastodon.write(
        [
            Message(id="ForeignId1", message="test message 3"),
            Message(id="ForeignId2", message="test message 4"),
        ]
    )
    assert posted_messages == ["test message 3", "test message 4"]
    assert mastodon.posted_message_ids == {"12121212", "23232323"}

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [
            {
                "id": "12121212",
                "content": "test message 3",
                "reblog": None,
                "in_reply_to_id": None,
            },
            {
                "id": "23232323",
                "content": "test message 4",
                "reblog": None,
                "in_reply_to_id": None,
            },
            {
                "id": "44554455",
                "content": "<p>test message 5</p> <p>test message 6</p>",
                "reblog": None,
                "in_reply_to_id": None,
            },
            {
                "id": "44554458",
                "content": "<p>test message 7</p> <p>test message 8</p>",
                "reblog": None,
                "in_reply_to_id": "13245678945613",
            },
        ],
    )

    messages = mastodon.read()

    assert messages == [Message(id="44554455", message="test message 5 test message 6")]
    assert mastodon.min_id == "12121212"
    assert mastodon.posted_message_ids == {"12121212", "23232323"}
