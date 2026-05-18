"""
Reusable helpers for validating and resizing image payloads.
"""

import io
from typing import Any, Final, Mapping, Optional, Sequence

from PIL import Image

DEFAULT_IMAGE_SCALE_FACTORS: Final[tuple[float, ...]] = (0.8, 0.75)
DEFAULT_IMAGE_QUALITY_STEPS: Final[tuple[int, ...]] = (85, 70)


def response_contains_image(
    response: Any,
    payload: bytes,
) -> bool:
    """
    Determine whether an HTTP response body appears to contain image data.

    The content type is trusted when it explicitly reports ``image/*``.
    Otherwise the payload is sniffed with Pillow.

    :param response: HTTP response-like object with an optional ``headers`` mapping
    :param payload: Response body bytes
    :return: ``True`` when the payload appears to be an image
    """

    headers = getattr(response, "headers", {}) or {}

    raw_content_type = ""
    if isinstance(headers, Mapping):
        raw_content_type = str(headers.get("Content-Type", ""))

    content_type = raw_content_type.split(";", 1)[0].strip().lower()
    if content_type.startswith("image/"):
        return True

    try:
        with Image.open(io.BytesIO(payload)) as image:
            return image.format is not None
    except Exception:  # pylint: disable=broad-except
        return False


def compress_image_to_size_limit(
    img_data: bytes,
    size_limit_bytes: int,
    scale_factors: Sequence[float] = DEFAULT_IMAGE_SCALE_FACTORS,
    quality_steps: Sequence[int] = DEFAULT_IMAGE_QUALITY_STEPS,
) -> Optional[bytes]:
    """
    Attempt to reduce an image payload until it fits within a byte limit.

    The output is re-encoded as JPEG after resizing and quality reduction.

    :param img_data: Original image bytes
    :param size_limit_bytes: Maximum allowed output size in bytes
    :param scale_factors: Resize factors to try, in order
    :param quality_steps: JPEG quality values to try, in order
    :return: Compressed image bytes, the original bytes if already within the limit,
        or ``None`` when compression fails
    """

    try:
        with Image.open(io.BytesIO(img_data)) as image:
            if len(img_data) <= size_limit_bytes:
                return img_data

            original_width, original_height = image.size

            for scale_factor in scale_factors:
                new_width = max(1, int(original_width * scale_factor))
                new_height = max(1, int(original_height * scale_factor))

                with image.resize(
                    (new_width, new_height), Image.Resampling.LANCZOS
                ) as resized_image:
                    output_image = _convert_image_for_jpeg(resized_image)

                    try:
                        for quality in quality_steps:
                            with io.BytesIO() as output:
                                output_image.save(
                                    output,
                                    format="JPEG",
                                    quality=quality,
                                    optimize=True,
                                )

                                if output.tell() <= size_limit_bytes:
                                    return output.getvalue()
                    finally:
                        if output_image is not resized_image:
                            output_image.close()

        return None
    except Exception:  # pylint: disable=broad-except
        return None


def _convert_image_for_jpeg(image: Image.Image) -> Image.Image:
    """
    Convert image modes unsupported by JPEG into a compatible RGB image.
    """

    if image.mode in {"RGB", "L"}:
        return image

    background = Image.new("RGB", image.size, (255, 255, 255))
    alpha_source = image.convert("RGBA")
    background.paste(alpha_source, mask=alpha_source.getchannel("A"))
    alpha_source.close()
    return background
