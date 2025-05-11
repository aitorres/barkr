"""
Module to implement unit tests for the Media class.
"""

from barkr.models.media import Media


def test_media() -> None:
    """
    Test that the Media class is initialized correctly
    """

    media_1 = Media(
        mime_type="image/jpeg",
        content=b"Hello, world!",
    )

    assert media_1.mime_type == "image/jpeg"
    assert media_1.content == b"Hello, world!"

    media_2 = Media(
        mime_type="video/mp4",
        content=b"Bonjour le monde!",
    )
    assert media_2.mime_type == "video/mp4"
    assert media_2.content == b"Bonjour le monde!"

    media_3 = Media(
        mime_type="image/png",
        content=b"Hola, mundo!",
    )
    assert media_3.mime_type == "image/png"
    assert media_3.content == b"Hola, mundo!"


def test_media_is_valid() -> None:
    """
    Test that the validation checks for the Media class
    are working correctly.
    """

    assert Media(
        mime_type="image/jpeg",
        content=b"Hello, world!",
    ).is_valid()

    assert Media(
        mime_type="video/mp4",
        content=b"Bonjour le monde!",
    ).is_valid()

    assert not Media(
        mime_type="image/jpeg",
        content=b"",
    ).is_valid()

    assert not Media(
        mime_type="",
        content=b"Hello, world!",
    ).is_valid()

    assert not Media(
        mime_type="unsupported/type",
        content=b"Hello, world!",
    ).is_valid()
