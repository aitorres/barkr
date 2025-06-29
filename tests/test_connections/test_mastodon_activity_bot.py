"""
Module to implement unit tests for the Mastodon Activity Bot connection class.
"""

import pytest

from barkr.connections import ConnectionMode, MastodonActivityBotConnection
from barkr.models import Message


def test_mastodon_activity_bot_init(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test the initialization of the Mastodon Activity Bot connection class.
    """

    with pytest.raises(
        NotImplementedError,
        match="MastodonActivityBotConnection only supports write mode.",
    ):
        MastodonActivityBotConnection(
            name="ActivityBot",
            modes=[ConnectionMode.READ],
            password="password",
            api_url="https://example.com",
        )

    with pytest.raises(
        NotImplementedError,
        match="MastodonActivityBotConnection only supports write mode.",
    ):
        MastodonActivityBotConnection(
            name="ActivityBot",
            modes=[ConnectionMode.READ, ConnectionMode.WRITE],
            password="password",
            api_url="https://example.com",
        )

    bot = MastodonActivityBotConnection(
        name="ActivityBot",
        modes=[ConnectionMode.WRITE],
        password="password",
        api_url="https://example.com",
    )
    assert bot.name == "ActivityBot"
    assert bot.modes == [ConnectionMode.WRITE]
    assert bot.password == "password"
    assert bot.api_url == "https://example.com"

    # Reading gives an empty list
    assert not bot.read()

    # We are allowed to write
    posted_messages: list[str] = []

    def mock_requests_post(_url: str, data: dict[str, str], *_args, **_kwargs):
        nonlocal posted_messages  # noqa: F824

        posted_messages.append(data["content"])
        return type("Response", (), {"status_code": 200})

    monkeypatch.setattr("requests.post", mock_requests_post)

    bot.write([Message("1", "Hello world!")])
    assert posted_messages == ["Hello world!"]
    bot.write([Message("2", "Hello world 2!")])
    assert posted_messages == ["Hello world!", "Hello world 2!"]

    # Handling errors
    def mock_requests_post_failure(
        _url: str,
        data: dict[str, str],
        *_args,
        **_kwargs  # pylint: disable=unused-argument
    ):
        return type("Response", (), {"status_code": 503, "text": "Service Unavailable"})

    monkeypatch.setattr("requests.post", mock_requests_post_failure)

    bot.write([Message("3", "This will fail!")])
    # No change in posted messages
    assert posted_messages == ["Hello world!", "Hello world 2!"]
