"""
Module to implement unit tests for the Mastodon Activity Bot connection class.
"""

import pytest

from barkr.connections import ConnectionMode, MastodonActivityBotConnection
from barkr.models import Media, Message


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

    bot = _build_bot()
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
        return _ok_response()

    monkeypatch.setattr("requests.post", mock_requests_post)

    bot.write([Message("1", "Hello world!", source_connection="test")])
    assert posted_messages == ["Hello world!"]
    bot.write([Message("2", "Hello world 2!", source_connection="test")])
    assert posted_messages == ["Hello world!", "Hello world 2!"]

    # Handling errors
    def mock_requests_post_failure(
        _url: str,
        data: dict[str, str],
        *_args,
        **_kwargs,  # pylint: disable=unused-argument
    ):
        return type(
            "Response",
            (),
            {"status_code": 503, "text": "Service Unavailable", "ok": False},
        )

    monkeypatch.setattr("requests.post", mock_requests_post_failure)

    bot.write([Message("3", "This will fail!", source_connection="test")])
    # No change in posted messages
    assert posted_messages == ["Hello world!", "Hello world 2!"]


def test_mastodon_activity_bot_post_with_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A message with a single valid image attachment should be uploaded as
    multipart form data with `image` and `alt` fields.
    """

    bot = _build_bot()
    captured: dict = {}

    def mock_post(_url, *_args, data=None, files=None, **_kwargs):
        captured["data"] = data
        captured["files"] = files
        return _ok_response()

    monkeypatch.setattr("requests.post", mock_post)

    image = Media(mime_type="image/png", content=b"abc", alt_text="hello")
    bot.write(
        [
            Message(
                "1",
                "with image",
                source_connection="test",
                media=[image],
            )
        ]
    )

    assert captured["data"]["content"] == "with image"
    assert captured["data"]["alt"] == "hello"
    assert captured["files"] is not None
    filename, content, mime = captured["files"]["image"]
    assert filename == "upload.png"
    assert content == b"abc"
    assert mime == "image/png"


def test_mastodon_activity_bot_post_with_multiple_images_uses_first(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """
    If a message has multiple valid images, only the first is uploaded
    and a warning is logged.
    """

    bot = _build_bot()
    captured: dict = {}

    def mock_post(_url, *_args, data=None, files=None, **_kwargs):
        captured["data"] = data
        captured["files"] = files
        return _ok_response()

    monkeypatch.setattr("requests.post", mock_post)

    media = [
        Media(mime_type="image/png", content=b"first", alt_text="a"),
        Media(mime_type="image/jpeg", content=b"second", alt_text="b"),
    ]

    with caplog.at_level("WARNING"):
        bot.write([Message("1", "two images", source_connection="test", media=media)])

    _, content, mime = captured["files"]["image"]
    assert content == b"first"
    assert mime == "image/png"
    assert captured["data"]["alt"] == "a"
    assert any("single image" in r.message for r in caplog.records)


def test_mastodon_activity_bot_post_skips_non_image_media(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """
    Non-image media (e.g. videos) are skipped with a warning, and the
    text-only post still goes through with no `files` payload.
    """

    bot = _build_bot()
    captured: dict = {}

    def mock_post(_url, *_args, data=None, files=None, **_kwargs):
        captured["data"] = data
        captured["files"] = files
        return _ok_response()

    monkeypatch.setattr("requests.post", mock_post)

    media = [Media(mime_type="video/mp4", content=b"vid", alt_text="")]

    with caplog.at_level("WARNING"):
        bot.write([Message("1", "video only", source_connection="test", media=media)])

    assert captured["files"] is None
    assert "alt" not in captured["data"]


def test_mastodon_activity_bot_post_image_only_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A message with empty text but a valid image should still be posted,
    confirming `MessageType.TEXT_MEDIA` allows media-only messages through.
    """

    bot = _build_bot()
    captured: dict = {}

    def mock_post(_url, *_args, data=None, files=None, **_kwargs):
        captured["data"] = data
        captured["files"] = files
        return _ok_response()

    monkeypatch.setattr("requests.post", mock_post)

    image = Media(mime_type="image/jpeg", content=b"img", alt_text="")
    bot.write([Message("1", "", source_connection="test", media=[image])])

    assert captured["data"]["content"] == ""
    assert captured["files"] is not None
    assert "alt" not in captured["data"]


def _build_bot() -> MastodonActivityBotConnection:
    return MastodonActivityBotConnection(
        name="ActivityBot",
        modes=[ConnectionMode.WRITE],
        password="password",
        api_url="https://example.com",
    )


def _ok_response():
    return type("Response", (), {"status_code": 302, "text": "OK", "ok": True})
