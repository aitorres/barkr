"""
Module to implement unit tests for the Mastodon connection class
"""

from typing import Any, Optional

import pytest
from mastodon import MastodonNetworkError
from mastodon.return_types import MediaAttachment
from requests.exceptions import RequestException

from barkr.connections import ConnectionMode, MastodonConnection
from barkr.connections.mastodon import (
    _get_media_list_from_status,
    _post_media_list_to_mastodon,
)
from barkr.models import Media, Message, MessageMetadata
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
                "media_attachments": [],
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
                "id": "55667788",
                "content": "test message 2",
                "reblog": None,
                "media_attachments": [],
                "in_reply_to_id": None,
                "visibility": "public",
                "language": None,
                "spoiler_text": "",
            },
            {
                "id": "11223344",
                "content": "test message 1",
                "reblog": None,
                "media_attachments": [],
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
            id="11223344", message="test message 1", source_connection="MastodonClass"
        ),
        Message(
            id="55667788", message="test message 2", source_connection="MastodonClass"
        ),
    ]
    assert mastodon.min_id == "55667788"

    posted_messages: list[str] = []
    posted_languages: list[Optional[str]] = []
    posted_labels: list[Optional[str]] = []
    posted_visibilities: list[Optional[str]] = []
    posted_media_ids: list[Optional[list[MediaAttachment]]] = []

    def status_post_mockup(_, message: str, *_args, **kwargs) -> dict[str, Any]:
        posted_messages.append(message)
        posted_languages.append(kwargs.get("language"))
        posted_labels.append(kwargs.get("spoiler_text"))
        posted_visibilities.append(kwargs.get("visibility"))
        posted_media_ids.append(kwargs.get("media_ids"))

        return {"id": "12121212" if message == "test message 3" else "23232323"}

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.status_post", status_post_mockup
    )

    mastodon.write(
        [
            Message(
                id="ForeignId1", message="test message 3", source_connection="test"
            ),
            Message(
                id="ForeignId2", message="test message 4", source_connection="test"
            ),
            Message(
                id="ForeignId3",
                message="test message 8",
                metadata=MessageMetadata(language="en"),
                source_connection="test",
            ),
            Message(
                id="ForeignId4",
                message="test message 7",
                metadata=MessageMetadata(label="test label"),
                source_connection="test",
            ),
            Message(
                id="ForeignId5",
                message="test message 5",
                metadata=MessageMetadata(visibility=MessageVisibility.UNLISTED),
                source_connection="test",
            ),
        ]
    )
    assert posted_messages == [
        "test message 3",
        "test message 4",
        "test message 8",
        "test message 7",
        "test message 5",
    ]
    assert posted_languages == [None, None, "en", None, None]
    assert posted_labels == ["", "", "", "test label", ""]
    assert mastodon.posted_message_ids == {"12121212", "23232323"}
    assert posted_media_ids == [[], [], [], [], []]
    assert posted_visibilities == [
        "public",
        "public",
        "public",
        "public",
        "unlisted",
    ]

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [
            {
                "id": "44554458",
                "content": "<p>test message 7</p> <p>test message 8</p>",
                "reblog": None,
                "media_attachments": [],
                "in_reply_to_id": "13245678945613",
                "language": None,
                "spoiler_text": "",
            },
            {
                "id": "44554455",
                "content": "<p>test message 5</p> <p>test message 6</p>",
                "reblog": None,
                "media_attachments": [],
                "in_reply_to_id": None,
                "visibility": "public",
                "language": None,
                "spoiler_text": "",
            },
            {
                "id": "23232323",
                "content": "test message 4",
                "reblog": None,
                "media_attachments": [],
                "in_reply_to_id": None,
                "visibility": "public",
                "language": None,
                "spoiler_text": "",
            },
            {
                "id": "12121212",
                "content": "test message 3",
                "reblog": None,
                "media_attachments": [],
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
            id="44554455",
            message="test message 5 test message 6",
            source_connection="MastodonClass",
        )
    ]
    assert mastodon.min_id == "44554458"
    assert mastodon.posted_message_ids == {"12121212", "23232323"}

    # Parses language successfully
    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [
            {
                "id": "93232323",
                "content": "test message 4",
                "reblog": None,
                "media_attachments": [],
                "in_reply_to_id": None,
                "visibility": "public",
                "language": None,
                "spoiler_text": "",
            },
            {
                "id": "73232323",
                "content": "test message 4",
                "reblog": None,
                "media_attachments": [],
                "in_reply_to_id": None,
                "visibility": "public",
                "language": "es",
                "spoiler_text": "",
            },
            {
                "id": "52121212",
                "content": "test message 3",
                "reblog": None,
                "media_attachments": [],
                "in_reply_to_id": None,
                "visibility": "public",
                "language": "en",
                "spoiler_text": "",
            },
        ],
    )
    assert mastodon.read() == [
        Message(
            id="52121212",
            message="test message 3",
            metadata=MessageMetadata(language="en"),
            source_connection="MastodonClass",
        ),
        Message(
            id="73232323",
            message="test message 4",
            metadata=MessageMetadata(language="es"),
            source_connection="MastodonClass",
        ),
        Message(
            id="93232323",
            message="test message 4",
            source_connection="MastodonClass",
        ),
    ]

    # Parses label successfully
    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [
            {
                "id": "73232323",
                "content": "test message 4",
                "reblog": None,
                "media_attachments": [],
                "in_reply_to_id": None,
                "visibility": "public",
                "language": None,
                "spoiler_text": "",
            },
            {
                "id": "52121212",
                "content": "test message 3",
                "reblog": None,
                "media_attachments": [],
                "in_reply_to_id": None,
                "visibility": "public",
                "language": None,
                "spoiler_text": "test label",
            },
        ],
    )
    assert mastodon.read() == [
        Message(
            id="52121212",
            message="test message 3",
            metadata=MessageMetadata(label="test label"),
            source_connection="MastodonClass",
        ),
        Message(
            id="73232323",
            message="test message 4",
            source_connection="MastodonClass",
        ),
    ]

    # Parses visibility successfully
    mastodon.min_id = None
    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.account_statuses",
        lambda *_args, **_kwargs: [
            {
                "id": "73232323",
                "content": "test message 4",
                "reblog": None,
                "media_attachments": [],
                "in_reply_to_id": None,
                "visibility": "direct",
                "language": None,
                "spoiler_text": "",
            },
            {
                "id": "73232323",
                "content": "test message 4",
                "reblog": None,
                "media_attachments": [],
                "in_reply_to_id": None,
                "visibility": "unlisted",
                "language": None,
                "spoiler_text": "",
            },
            {
                "id": "52121212",
                "content": "test message 3",
                "reblog": None,
                "media_attachments": [],
                "in_reply_to_id": None,
                "visibility": "private",
                "language": None,
                "spoiler_text": "",
            },
        ],
    )
    assert mastodon.read() == [
        Message(
            id="52121212",
            message="test message 3",
            metadata=MessageMetadata(visibility=MessageVisibility.PRIVATE),
            source_connection="MastodonClass",
        ),
        Message(
            id="73232323",
            message="test message 4",
            metadata=MessageMetadata(visibility=MessageVisibility.UNLISTED),
            source_connection="MastodonClass",
        ),
        Message(
            id="73232323",
            message="test message 4",
            metadata=MessageMetadata(visibility=MessageVisibility.DIRECT),
            source_connection="MastodonClass",
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
            Message(
                id="ForeignId1", message="test message 3", source_connection="test"
            ),
            Message(
                id="ForeignId2", message="test message 4", source_connection="test"
            ),
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
                Message(
                    id="ForeignId1", message="test message 3", source_connection="test"
                ),
                Message(
                    id="ForeignId2", message="test message 4", source_connection="test"
                ),
            ]
        )


def test_post_media_list_to_mastodon(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test that the helper function _post_media_list_to_mastodon
    correctly prepares and posts media to Mastodon
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

    mastodon_service = mastodon.service
    assert mastodon_service is not None

    # Case: empty media list
    assert not _post_media_list_to_mastodon(mastodon_service, [])

    # Case: invalid media list
    assert not _post_media_list_to_mastodon(
        mastodon_service, [Media("invalid/type", b"invalid content")]
    )

    # Case: valid media list
    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.media_post",
        lambda *_args, **_kwargs: MediaAttachment(
            id="1234567890",
            type="image/jpeg",
            url="https://example.com/media/1234567890",
        ),
    )

    media_list = [
        Media("image/jpeg", b"test content 1"),
        Media("image/png", b"test content 2"),
    ]

    media_ids = _post_media_list_to_mastodon(mastodon_service, media_list)

    assert len(media_ids) == 2

    # Case: there is an exception for one of the media
    def mock_media_post(*_args, **kwargs) -> MediaAttachment:
        media_file = kwargs.get("media_file")
        mime_type = kwargs.get("mime_type")

        if media_file == b"test content 1":
            raise MastodonNetworkError("Test exception")

        return MediaAttachment(
            id="1234567890", type=mime_type, url="https://example.com/media/1234567890"
        )

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.media_post",
        mock_media_post,
    )

    media_list = [
        Media("image/jpeg", b"test content 1"),
        Media("image/png", b"test content 2"),
    ]

    media_ids = _post_media_list_to_mastodon(mastodon_service, media_list)

    assert len(media_ids) == 1
    assert media_ids[0].id == "1234567890"
    assert media_ids[0].type == "image/png"
    assert media_ids[0].url == "https://example.com/media/1234567890"


def test_get_media_list_from_status(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test that the helper function _get_media_list_from_status
    correctly extracts media from a Mastodon status
    """

    # Case: empty media list
    assert not _get_media_list_from_status({"media_attachments": []})

    # Case: unsupported media type
    status = {
        "id": "1234567890",
        "media_attachments": [
            {"type": "unsupported", "url": "https://example.com/media/1234567890"},
        ],
    }
    assert not _get_media_list_from_status(status)

    # Case: valid media list
    monkeypatch.setattr(
        "requests.get",
        lambda url, *_args, **_kwargs: type(
            "Response", (object,), {"content": b"test content", "status_code": 200}
        ),
    )
    status = {
        "media_attachments": [
            {
                "type": "image",
                "description": "text",
                "url": "https://example.com/media/1234567890.jpg",
            },
            {
                "type": "image",
                "description": "text",
                "url": "https://example.com/media/0987654321.png",
            },
        ]
    }

    media_list = _get_media_list_from_status(status)

    assert len(media_list) == 2
    assert media_list[0].mime_type == "image/jpeg"
    assert media_list[0].content == b"test content"
    assert media_list[1].mime_type == "image/png"
    assert media_list[1].content == b"test content"

    # Case: mime type cannot be determined from URL
    monkeypatch.setattr(
        "requests.get",
        lambda url, *_args, **_kwargs: type(
            "Response", (object,), {"content": b"test content", "status_code": 200}
        ),
    )
    status = {
        "media_attachments": [
            {
                "type": "image",
                "description": "text",
                "url": "https://example.com/media/1234567890",
            },
            {
                "type": "image",
                "description": "text",
                "url": "https://example.com/media/0987654321.png",
            },
        ]
    }
    media_list = _get_media_list_from_status(status)
    assert len(media_list) == 1
    assert media_list[0].mime_type == "image/png"
    assert media_list[0].content == b"test content"

    # Case: there's an exception for one of the media
    def mock_get(*_args, **_kwargs) -> Any:
        if _args[0] == "https://example.com/media/1234567890.jpg":
            raise RequestException("Test exception")

        return type(
            "Response", (object,), {"content": b"test content", "status_code": 200}
        )

    monkeypatch.setattr("requests.get", mock_get)

    status = {
        "media_attachments": [
            {
                "type": "image",
                "description": "text",
                "url": "https://example.com/media/1234567890.jpg",
            },
            {
                "type": "image",
                "description": "text",
                "url": "https://example.com/media/0987654321.png",
            },
        ]
    }

    media_list = _get_media_list_from_status(status)

    assert len(media_list) == 1
    assert media_list[0].mime_type == "image/png"
    assert media_list[0].content == b"test content"
    assert media_list[0].alt_text == "text"


def test_mastodon_skips_reply_when_parent_not_crossposted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Test that a reply message is skipped when the parent wasn't crossposted.
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
        "MastodonTest",
        [ConnectionMode.WRITE],
        "test_token",
        "https://example.com",
    )

    posted_messages: list[str] = []

    def status_post_mockup(_, message: str, *_args, **_kwargs) -> dict[str, Any]:
        posted_messages.append(message)
        return {"id": "posted_id"}

    monkeypatch.setattr(
        "barkr.connections.mastodon.Mastodon.status_post", status_post_mockup
    )

    mastodon.write(
        [
            Message(
                id="reply1",
                message="This is a reply",
                source_connection="other_connection",
                reply_to_id="parent_id_not_crossposted",
            ),
        ]
    )

    assert not posted_messages
