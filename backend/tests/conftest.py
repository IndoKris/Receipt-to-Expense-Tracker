"""Pytest fixtures and environment configuration."""

import io
import os
import sys
from pathlib import Path
import pytest
from PIL import Image

# Ensure backend root directory is on sys.path
backend_root = str(Path(__file__).parent.parent.resolve())
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

# Ensure environment is configured for test mode before importing application code
os.environ["PROVIDER"] = "fake"
os.environ["APP_TOKEN"] = "test-token-123"
os.environ["MAX_UPLOAD_MB"] = "6"
os.environ["RATE_LIMIT_PER_MIN"] = "100"
os.environ["MODEL_TIMEOUT_S"] = "5.0"


@pytest.fixture
def test_token() -> str:
    """Return default test auth token."""
    return "test-token-123"


@pytest.fixture
def sample_jpeg_bytes() -> bytes:
    """Return a valid minimal JPEG image as bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def sample_png_bytes() -> bytes:
    """Return a valid minimal PNG image as bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    img.save(buf, format="PNG")
    return buf.getvalue()
