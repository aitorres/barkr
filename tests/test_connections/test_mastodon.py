"""
Module to implement unit tests for the Mastodon connection class
"""

import pytest

from hermes.connections.mastodon import ConnectionMode, MastodonConnection


def test_mastodon_connection_init(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Basic unit tests for the MastodonConnection class
    """

    monkeypatch.setattr(
        "hermes.connections.mastodon.Mastodon.account_verify_credentials",
        lambda _: {"id": "1234567890"},
    )

    monkeypatch.setattr(
        "hermes.connections.mastodon.Mastodon.account_statuses",
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
        "hermes.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [
            {"id": "11223344", "content": "test message 1"},
            {"id": "55667788", "content": "test message 2"},
        ],
    )

    messages = mastodon.read()

    assert messages == ["test message 1", "test message 2"]
    assert mastodon.min_id == "55667788"

    posted_messages: list[str] = []
    monkeypatch.setattr(
        "hermes.connections.mastodon.Mastodon.status_post",
        lambda _, message: posted_messages.append(message),
    )

    mastodon.write(["test message 3", "test message 4"])
    assert posted_messages == ["test message 3", "test message 4"]
