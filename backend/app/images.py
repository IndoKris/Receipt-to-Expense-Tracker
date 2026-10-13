"""Image upload verification, dimension checking, resizing, and normalization."""

import io
from typing import Set
from PIL import Image, UnidentifiedImageError

ALLOWED_FORMATS: Set[str] = {"JPEG", "PNG", "WEBP"}
MAX_DIMENSION: int = 8000
MAX_NORMALIZED_SIDE: int = 1600


class ImageError(Exception):
    """Base exception for image processing errors."""
    pass


class ImageTooLargeError(ImageError):
    """Raised when uploaded image file size exceeds the configured maximum."""
    pass


class UnsupportedImageError(ImageError):
    """Raised when uploaded file is corrupted, animated, oversized, or unsupported format."""
    pass


def validate_and_normalize_image(image_bytes: bytes, max_mb: int = 6) -> bytes:
    """
    Validate uploaded image bytes and normalize to sanitized JPEG bytes.

    Steps:
    1. Verify raw byte size does not exceed max_mb.
    2. Verify decodability with Pillow (Image.open().verify() then reopen).
    3. Check format against allowlist (JPEG, PNG, WEBP only).
    4. Reject animated images (multiple frames).
    5. Reject images with dimensions > 8000px.
    6. Resize longest side to <= 1600px while preserving aspect ratio.
    7. Convert to RGB and re-encode to JPEG without EXIF metadata.
    """
    if not image_bytes:
        raise UnsupportedImageError("Empty image payload provided.")

    max_bytes = max_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise ImageTooLargeError(
            f"Image payload size ({len(image_bytes)} bytes) exceeds maximum allowed size of {max_mb} MB."
        )

    # 1. Verify decode with Pillow
    buf = io.BytesIO(image_bytes)
    try:
        with Image.open(buf) as img_check:
            img_format = img_check.format
            img_check.verify()
    except Exception as e:
        raise UnsupportedImageError(f"File could not be verified as a valid image: {e}") from e

    # 2. Re-open after verify() per Pillow requirement
    buf.seek(0)
    try:
        img = Image.open(buf)
        img.load()  # force full load into memory
    except Exception as e:
        raise UnsupportedImageError(f"Failed to load verified image: {e}") from e

    # 3. Format allowlist
    # Note: img.format might be None after load on some Pillow versions, use img_format if needed
    detected_format = (img.format or img_format or "").upper()
    if detected_format not in ALLOWED_FORMATS:
        raise UnsupportedImageError(
            f"Unsupported image format: '{detected_format}'. Allowed formats are: {', '.join(sorted(ALLOWED_FORMATS))}."
        )

    # 4. Reject animated images
    is_animated = getattr(img, "is_animated", False)
    n_frames = getattr(img, "n_frames", 1)
    if is_animated and n_frames > 1:
        raise UnsupportedImageError("Animated images are not supported.")

    # 5. Check dimensions
    width, height = img.size
    if width <= 0 or height <= 0:
        raise UnsupportedImageError("Invalid image dimensions.")
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise UnsupportedImageError(
            f"Image dimensions ({width}x{height}) exceed maximum allowed dimension of {MAX_DIMENSION}px."
        )

    # 6. Resize if longest side > 1600px
    longest_side = max(width, height)
    if longest_side > MAX_NORMALIZED_SIDE:
        scale = MAX_NORMALIZED_SIDE / float(longest_side)
        new_width = max(1, int(round(width * scale)))
        new_height = max(1, int(round(height * scale)))
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # 7. Convert to RGB and re-encode to JPEG (stripping EXIF)
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Clear EXIF from info dict if present
    img.info.pop("exif", None)

    out_buf = io.BytesIO()
    img.save(out_buf, format="JPEG", quality=85, optimize=True)
    return out_buf.getvalue()
