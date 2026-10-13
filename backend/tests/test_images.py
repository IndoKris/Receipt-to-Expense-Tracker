"""Unit tests for image upload processing and sanitization."""

import io
import pytest
from PIL import Image

from app.images import (
    ImageTooLargeError,
    UnsupportedImageError,
    validate_and_normalize_image,
)


def test_valid_jpeg_processed_successfully():
    """Standard JPEG image is normalized and returns valid JPEG bytes."""
    buf = io.BytesIO()
    original = Image.new("RGB", (800, 600), color=(200, 100, 50))
    original.save(buf, format="JPEG")

    result = validate_and_normalize_image(buf.getvalue(), max_mb=6)
    assert isinstance(result, bytes)
    assert len(result) > 0

    reopened = Image.open(io.BytesIO(result))
    assert reopened.format == "JPEG"
    assert reopened.size == (800, 600)


def test_valid_png_converted_to_jpeg():
    """PNG image is accepted and re-encoded to JPEG."""
    buf = io.BytesIO()
    original = Image.new("RGBA", (500, 500), color=(100, 150, 200, 255))
    original.save(buf, format="PNG")

    result = validate_and_normalize_image(buf.getvalue(), max_mb=6)
    reopened = Image.open(io.BytesIO(result))
    assert reopened.format == "JPEG"
    assert reopened.mode == "RGB"
    assert reopened.size == (500, 500)


def test_valid_webp_converted_to_jpeg():
    """WebP image is accepted and re-encoded to JPEG."""
    buf = io.BytesIO()
    original = Image.new("RGB", (400, 300), color=(50, 100, 150))
    original.save(buf, format="WEBP")

    result = validate_and_normalize_image(buf.getvalue(), max_mb=6)
    reopened = Image.open(io.BytesIO(result))
    assert reopened.format == "JPEG"
    assert reopened.size == (400, 300)


def test_image_resize_down_to_1600():
    """Image larger than 1600px on longest side is scaled down preserving aspect ratio."""
    buf = io.BytesIO()
    # 3200 x 2400 -> scale to 1600 x 1200
    original = Image.new("RGB", (3200, 2400), color=(10, 20, 30))
    original.save(buf, format="JPEG")

    result = validate_and_normalize_image(buf.getvalue(), max_mb=6)
    reopened = Image.open(io.BytesIO(result))
    assert reopened.size == (1600, 1200)
    assert max(reopened.size) <= 1600


def test_exif_data_stripped():
    """EXIF metadata such as GPS / camera info is stripped from the output JPEG."""
    buf = io.BytesIO()
    original = Image.new("RGB", (300, 300), color=(255, 255, 255))

    # Add mock EXIF
    exif_obj = original.getexif()
    exif_obj[0x010E] = "Test Image Description"  # ImageDescription tag
    original.save(buf, format="JPEG", exif=exif_obj)

    result = validate_and_normalize_image(buf.getvalue(), max_mb=6)
    reopened = Image.open(io.BytesIO(result))
    output_exif = reopened.getexif()
    # EXIF data should be empty
    assert len(output_exif) == 0


def test_animated_image_rejected():
    """Multi-frame animated image is rejected."""
    buf = io.BytesIO()
    f1 = Image.new("RGB", (100, 100), color=(255, 0, 0))
    f2 = Image.new("RGB", (100, 100), color=(0, 255, 0))
    # Save as multi-frame GIF
    f1.save(buf, format="GIF", save_all=True, append_images=[f2])

    with pytest.raises(UnsupportedImageError):
        validate_and_normalize_image(buf.getvalue(), max_mb=6)


def test_huge_dimensions_rejected():
    """Image with dimension > 8000px is rejected."""
    buf = io.BytesIO()
    # 8500 x 100 is over dimension limit
    original = Image.new("RGB", (8500, 100), color=(0, 0, 0))
    original.save(buf, format="JPEG")

    with pytest.raises(UnsupportedImageError) as exc_info:
        validate_and_normalize_image(buf.getvalue(), max_mb=6)
    assert "8000px" in str(exc_info.value)


def test_oversized_payload_rejected():
    """Payload exceeding max_mb is rejected with ImageTooLargeError."""
    huge_bytes = b"0" * (1 * 1024 * 1024 + 10)  # slightly over 1MB
    with pytest.raises(ImageTooLargeError):
        validate_and_normalize_image(huge_bytes, max_mb=1)


def test_corrupted_image_bytes_rejected():
    """Corrupted garbage bytes are rejected with UnsupportedImageError."""
    corrupted = b"\xFF\xD8\xFF\xE0" + b"garbage" * 50
    with pytest.raises(UnsupportedImageError):
        validate_and_normalize_image(corrupted, max_mb=6)
