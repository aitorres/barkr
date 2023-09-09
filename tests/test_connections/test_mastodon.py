"""
Module to implement unit tests for the Mastodon connection class
"""

from typing import Any

import pytest

from barkr.connections.mastodon import ConnectionMode, MastodonConnection


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
        lambda *_args, **_kwargs: [{"id": "987654321"}],
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
        lambda *_args, **_kwargs: [
            {"id": "11223344", "content": "test message 1"},
            {"id": "55667788", "content": "test message 2"},
        ],
    )

    messages = mastodon.read()

    assert messages == ["test message 1", "test message 2"]
    assert mastodon.min_id == "11223344"

    posted_messages: list[str] = []

    def status_post_mockup(_, message: str) -> dict[str, Any]:
        posted_messages.append(message)

        return {"id": "12121212" if message == "test message 3" else "23232323"}

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.status_post", status_post_mockup
    )

    mastodon.write(["test message 3", "test message 4"])
    assert posted_messages == ["test message 3", "test message 4"]
    assert mastodon.posted_message_ids == {"12121212", "23232323"}

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [
            {"id": "12121212", "content": "test message 3"},
            {"id": "23232323", "content": "test message 4"},
            {"id": "44554455", "content": "test message 5"},
        ],
    )

    messages = mastodon.read()

    assert messages == ["test message 5"]
    assert mastodon.min_id == "12121212"
    assert mastodon.posted_message_ids == set()
