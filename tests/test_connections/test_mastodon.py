"""
Module to implement unit tests for the Mastodon connection class
"""

from typing import Any, Optional

import pytest
from mastodon import MastodonNetworkError

from barkr.connections import ConnectionMode, MastodonConnection
from barkr.models import Message
from barkr.models.message import MessageVisibility


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
                "visibility": "public",
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
                "visibility": "public",
                "language": None,
                "spoiler_text": "",
            },
            {
                "id": "55667788",
                "content": "test message 2",
                "reblog": None,
                "in_reply_to_id": None,
                "visibility": "public",
                "language": None,
                "spoiler_text": "",
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
    posted_languages: list[Optional[str]] = []
    posted_labels: list[Optional[str]] = []
    posted_visibilities: list[Optional[str]] = []

    def status_post_mockup(
        _,
        message: str,
        language: Optional[str] = None,
        spoiler_text: Optional[str] = None,
        visibility: Optional[str] = None,
    ) -> dict[str, Any]:
        posted_messages.append(message)
        posted_languages.append(language)
        posted_labels.append(spoiler_text)
        posted_visibilities.append(visibility)

        return {"id": "12121212" if message == "test message 3" else "23232323"}

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.status_post", status_post_mockup
    )

    mastodon.write(
        [
            Message(id="ForeignId1", message="test message 3"),
            Message(id="ForeignId2", message="test message 4"),
            Message(id="ForeignId3", message="test message 8", language="en"),
            Message(id="ForeignId4", message="test message 7", label="test label"),
        ]
    )
    assert posted_messages == [
        "test message 3",
        "test message 4",
        "test message 8",
        "test message 7",
    ]
    assert posted_languages == [None, None, "en", None]
    assert posted_labels == ["", "", "", "test label"]
    assert mastodon.posted_message_ids == {"12121212", "23232323"}

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [
            {
                "id": "12121212",
                "content": "test message 3",
                "reblog": None,
                "in_reply_to_id": None,
                "visibility": "public",
                "language": None,
                "spoiler_text": "",
            },
            {
                "id": "23232323",
                "content": "test message 4",
                "reblog": None,
                "in_reply_to_id": None,
                "visibility": "public",
                "language": None,
                "spoiler_text": "",
            },
            {
                "id": "44554455",
                "content": "<p>test message 5</p> <p>test message 6</p>",
                "reblog": None,
                "in_reply_to_id": None,
                "visibility": "public",
                "language": None,
                "spoiler_text": "",
            },
            {
                "id": "44554458",
                "content": "<p>test message 7</p> <p>test message 8</p>",
                "reblog": None,
                "in_reply_to_id": "13245678945613",
                "language": None,
                "spoiler_text": "",
            },
        ],
    )

    messages = mastodon.read()

    assert messages == [Message(id="44554455", message="test message 5 test message 6")]
    assert mastodon.min_id == "12121212"
    assert mastodon.posted_message_ids == {"12121212", "23232323"}

    # Parses language successfully
    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [
            {
                "id": "52121212",
                "content": "test message 3",
                "reblog": None,
                "in_reply_to_id": None,
                "visibility": "public",
                "language": "en",
                "spoiler_text": "",
            },
            {
                "id": "73232323",
                "content": "test message 4",
                "reblog": None,
                "in_reply_to_id": None,
                "visibility": "public",
                "language": "es",
                "spoiler_text": "",
            },
            {
                "id": "93232323",
                "content": "test message 4",
                "reblog": None,
                "in_reply_to_id": None,
                "visibility": "public",
                "language": None,
                "spoiler_text": "",
            },
        ],
    )
    messages = mastodon.read()
    assert messages == [
        Message(id="52121212", message="test message 3", language="en", label=None),
        Message(id="73232323", message="test message 4", language="es", label=None),
        Message(id="93232323", message="test message 4", language=None, label=None),
    ]

    # Parses label successfully
    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [
            {
                "id": "52121212",
                "content": "test message 3",
                "reblog": None,
                "in_reply_to_id": None,
                "visibility": "public",
                "language": None,
                "spoiler_text": "test label",
            },
            {
                "id": "73232323",
                "content": "test message 4",
                "reblog": None,
                "in_reply_to_id": None,
                "visibility": "public",
                "language": None,
                "spoiler_text": "",
            },
        ],
    )
    messages = mastodon.read()
    assert messages == [
        Message(
            id="52121212", message="test message 3", language=None, label="test label"
        ),
        Message(id="73232323", message="test message 4", language=None, label=None),
    ]

    # Parses visibility successfully
    mastodon.min_id = None
    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [
            {
                "id": "52121212",
                "content": "test message 3",
                "reblog": None,
                "in_reply_to_id": None,
                "visibility": "private",
                "language": None,
                "spoiler_text": "",
            },
            {
                "id": "73232323",
                "content": "test message 4",
                "reblog": None,
                "in_reply_to_id": None,
                "visibility": "unlisted",
                "language": None,
                "spoiler_text": "",
            },
            {
                "id": "73232323",
                "content": "test message 4",
                "reblog": None,
                "in_reply_to_id": None,
                "visibility": "direct",
                "language": None,
                "spoiler_text": "",
            },
        ],
    )
    messages = mastodon.read()
    assert messages == [
        Message(
            id="52121212",
            message="test message 3",
            language=None,
            label=None,
            visibility=MessageVisibility.PRIVATE,
        ),
        Message(
            id="73232323",
            message="test message 4",
            language=None,
            label=None,
            visibility=MessageVisibility.UNLISTED,
        ),
        Message(
            id="73232323",
            message="test message 4",
            language=None,
            label=None,
            visibility=MessageVisibility.DIRECT,
        ),
    ]


def test_mastodon_handles_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test that, on a post write, Mastodon can retry posting the message
    whenever an exception is raised
    """

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_verify_credentials",
        lambda _: {"id": "1234567890"},
    )

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [],
    )

    mastodon = MastodonConnection(
        "MastodonClass",
        [ConnectionMode.WRITE],
        "test_token",
        "https://example.com",
    )
    assert mastodon.name == "MastodonClass"
    assert mastodon.account_id == "1234567890"
    assert mastodon.min_id is None
    assert mastodon.posted_message_ids == set()

    posted_messages: list[str] = []
    current_attempts: int = 0
    total_attempts: int = 0

    def status_post_mockup(_, message: str, *_args, **_kwargs) -> dict[str, Any]:
        nonlocal current_attempts
        nonlocal total_attempts

        total_attempts += 1

        if current_attempts < 2:
            current_attempts += 1
            raise MastodonNetworkError("Test exception")

        posted_messages.append(message)
        current_attempts = 0

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
    assert current_attempts == 0
    assert total_attempts == 6


def test_mastodon_handles_retries_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test that, on a post write, Mastodon surfaces the exception if
    the maximum number of retries is reached
    """

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_verify_credentials",
        lambda _: {"id": "1234567890"},
    )

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [],
    )

    mastodon = MastodonConnection(
        "MastodonClass",
        [ConnectionMode.WRITE],
        "test_token",
        "https://example.com",
    )
    assert mastodon.name == "MastodonClass"
    assert mastodon.account_id == "1234567890"
    assert mastodon.min_id is None
    assert mastodon.posted_message_ids == set()

    total_attempts: int = 0

    def status_post_mockup(_, _message: str, *_args, **_kwargs) -> dict[str, Any]:
        nonlocal total_attempts

        total_attempts += 1
        raise MastodonNetworkError("Test exception")

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.status_post", status_post_mockup
    )

    with pytest.raises(MastodonNetworkError, match="Test exception"):
        mastodon.write(
            [
                Message(id="ForeignId1", message="test message 3"),
                Message(id="ForeignId2", message="test message 4"),
            ]
        )
