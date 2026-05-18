"""
Unit tests for reusable image helper functions.
"""

import io
from dataclasses import dataclass
from typing import Optional

import pytest
from PIL import Image

from barkr.utils.image import compress_image_to_size_limit, response_contains_image


@dataclass(frozen=True)
class MockResponse:
    """Minimal HTTP response mock with headers."""

    headers: Optional[dict[str, str]] = None


def test_response_contains_image_with_image_content_type() -> None:
    """Explicit image content types should be accepted."""

    response = MockResponse(headers={"Content-Type": "image/jpeg; charset=utf-8"})
    assert response_contains_image(response, b"not-actually-checked") is True


def test_response_contains_image_sniffs_payload_without_image_content_type() -> None:
    """Valid image bytes should be accepted even without an image content type."""

    output = io.BytesIO()
    Image.new("RGB", (16, 16), color="red").save(output, "PNG")

    response = MockResponse(headers={"Content-Type": "application/octet-stream"})
    assert response_contains_image(response, output.getvalue()) is True


def test_response_contains_image_rejects_non_image_payload() -> None:
    """Non-image bytes should be rejected when content type is not image/*."""

    response = MockResponse(headers={"Content-Type": "text/html"})
    assert response_contains_image(response, b"<html>not an image</html>") is False


def test_compress_image_to_size_limit_handles_rgba_images() -> None:
    """Compression should support images that need mode conversion for JPEG."""

    output = io.BytesIO()
    Image.new("RGBA", (800, 800), color=(255, 0, 0, 128)).save(output, "PNG")

    result = compress_image_to_size_limit(
        output.getvalue(),
        size_limit_bytes=20_000,
        scale_factors=(0.5,),
        quality_steps=(70,),
    )

    assert result is not None
    assert len(result) <= 20_000


def test_compress_image_to_size_limit_keeps_small_images() -> None:
    """Small images should pass through without needing recompression."""

    output = io.BytesIO()
    Image.new("RGB", (100, 100), color="red").save(output, "JPEG", quality=95)

    original_data = output.getvalue()
    result = compress_image_to_size_limit(original_data, 1_000_000)

    assert result == original_data
    assert len(result) <= 1_000_000


def test_compress_image_to_size_limit_returns_none_when_target_not_reached() -> None:
    """Compression should fail cleanly when the target size is too small."""

    output = io.BytesIO()
    Image.new("RGB", (400, 400), color="red").save(output, "JPEG", quality=95)

    assert (
        compress_image_to_size_limit(
            output.getvalue(),
            size_limit_bytes=10,
            scale_factors=(0.9,),
            quality_steps=(90,),
        )
        is None
    )


def test_compress_image_to_size_limit_returns_none_on_image_open_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Image decode failures should return None."""

    def mock_image_open(*_args, **_kwargs):
        raise ValueError("Invalid image")

    monkeypatch.setattr("barkr.utils.image.Image.open", mock_image_open)
    assert compress_image_to_size_limit(b"bad image", 1000) is None
