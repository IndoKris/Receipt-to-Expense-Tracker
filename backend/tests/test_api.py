"""Integration tests for FastAPI endpoints."""

import io
import json
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import get_settings
from app.main import app, get_provider, get_rate_limiter
from app.providers.base import UpstreamError, UpstreamTimeoutError
from app.providers.fake import FakeProvider
from app.ratelimit import RateLimiter


@pytest.fixture
def client():
    """Create test client with clean rate limiter."""
    limiter = RateLimiter(rate_per_min=100)
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def test_healthz(client):
    """GET /healthz should return 200 ok."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_extract_happy_path_receipt(client, sample_jpeg_bytes, test_token):
    """POST /v1/extract with valid token and image should return 200 with extracted receipt."""
    provider = FakeProvider()
    app.dependency_overrides[get_provider] = lambda: provider

    files = {"image": ("receipt.jpg", sample_jpeg_bytes, "image/jpeg")}
    data = {"hint": "receipt"}
    headers = {"X-App-Token": test_token}

    resp = client.post("/v1/extract", files=files, data=data, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["readable"] is True
    assert body["document_type"] == "receipt"
    assert body["fields"]["merchant"]["value"] == "Corner Bakery"
    assert body["fields"]["amount"]["value"] == "15.50"
    assert body["fields"]["currency"]["value"] == "USD"
    assert "request_id" in body


def test_extract_happy_path_payment_screenshot(client, sample_jpeg_bytes, test_token):
    """POST /v1/extract with payment screenshot hint returns verified screenshot fields."""
    provider = FakeProvider()
    app.dependency_overrides[get_provider] = lambda: provider

    files = {"image": ("upi.jpg", sample_jpeg_bytes, "image/jpeg")}
    data = {"hint": "payment_screenshot"}
    headers = {"X-App-Token": test_token}

    resp = client.post("/v1/extract", files=files, data=data, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["readable"] is True
    assert body["document_type"] == "payment_screenshot"
    assert body["fields"]["merchant"]["value"] == "Chai Point"
    assert body["fields"]["payment_status"]["value"] == "success"
    assert "status_unverified" in body["warnings"]


def test_extract_unauthorized_missing_token(client, sample_jpeg_bytes):
    """POST /v1/extract without token returns 401."""
    files = {"image": ("receipt.jpg", sample_jpeg_bytes, "image/jpeg")}
    resp = client.post("/v1/extract", files=files, data={"hint": "auto"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"
    assert resp.json()["error"]["retryable"] is False


def test_extract_unauthorized_invalid_token(client, sample_jpeg_bytes):
    """POST /v1/extract with bad token returns 401."""
    files = {"image": ("receipt.jpg", sample_jpeg_bytes, "image/jpeg")}
    headers = {"X-App-Token": "completely-wrong-token"}
    resp = client.post("/v1/extract", files=files, data={"hint": "auto"}, headers=headers)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_extract_too_large(client, test_token):
    """POST /v1/extract with payload exceeding MAX_UPLOAD_MB returns 413."""
    settings = get_settings()
    # Create payload slightly larger than configured max
    oversized = b"X" * (settings.max_upload_mb * 1024 * 1024 + 1024)
    files = {"image": ("huge.jpg", oversized, "image/jpeg")}
    headers = {"X-App-Token": test_token}

    resp = client.post("/v1/extract", files=files, data={"hint": "auto"}, headers=headers)
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "too_large"
    assert resp.json()["error"]["retryable"] is False


def test_extract_unsupported_format(client, test_token):
    """POST /v1/extract with non-image file returns 415."""
    files = {"image": ("text.txt", b"This is plain text, not an image", "text/plain")}
    headers = {"X-App-Token": test_token}

    resp = client.post("/v1/extract", files=files, data={"hint": "auto"}, headers=headers)
    assert resp.status_code == 415
    assert resp.json()["error"]["code"] == "unsupported"
    assert resp.json()["error"]["retryable"] is False


def test_extract_rate_limited(client, sample_jpeg_bytes, test_token):
    """POST /v1/extract exceeding token bucket returns 429 with Retry-After header."""
    strict_limiter = RateLimiter(rate_per_min=1)
    app.dependency_overrides[get_rate_limiter] = lambda: strict_limiter
    provider = FakeProvider()
    app.dependency_overrides[get_provider] = lambda: provider

    files = {"image": ("receipt.jpg", sample_jpeg_bytes, "image/jpeg")}
    headers = {"X-App-Token": test_token}

    # First request consumes the single token
    resp1 = client.post("/v1/extract", files=files, data={"hint": "auto"}, headers=headers)
    assert resp1.status_code == 200

    # Second immediate request should be rate limited
    files2 = {"image": ("receipt.jpg", sample_jpeg_bytes, "image/jpeg")}
    resp2 = client.post("/v1/extract", files=files2, data={"hint": "auto"}, headers=headers)
    assert resp2.status_code == 429
    assert resp2.json()["error"]["code"] == "rate_limited"
    assert resp2.json()["error"]["retryable"] is True
    assert "Retry-After" in resp2.headers


def test_extract_upstream_timeout_504(client, sample_jpeg_bytes, test_token):
    """POST /v1/extract when model provider times out returns 504."""
    provider = FakeProvider(error=UpstreamTimeoutError("Timeout contacting model"))
    app.dependency_overrides[get_provider] = lambda: provider

    files = {"image": ("receipt.jpg", sample_jpeg_bytes, "image/jpeg")}
    headers = {"X-App-Token": test_token}

    resp = client.post("/v1/extract", files=files, data={"hint": "auto"}, headers=headers)
    assert resp.status_code == 504
    assert resp.json()["error"]["code"] == "upstream_timeout"
    assert resp.json()["error"]["retryable"] is True


def test_extract_upstream_error_502(client, sample_jpeg_bytes, test_token):
    """POST /v1/extract when Gemini API errors returns 502."""
    provider = FakeProvider(error=UpstreamError("API quota exhausted"))
    app.dependency_overrides[get_provider] = lambda: provider

    files = {"image": ("receipt.jpg", sample_jpeg_bytes, "image/jpeg")}
    headers = {"X-App-Token": test_token}

    resp = client.post("/v1/extract", files=files, data={"hint": "auto"}, headers=headers)
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "upstream_error"
    assert resp.json()["error"]["retryable"] is True


def test_extract_invalid_json_then_valid_retry_200(client, sample_jpeg_bytes, test_token):
    """When first model response is malformed, retry should succeed and return 200."""
    valid_json = json.dumps({
        "readable": True,
        "document_type": "receipt",
        "merchant": {"value": "Retry Bakery", "confidence": 0.9},
        "amount": {"value": "20.00", "confidence": 0.95},
        "currency": {"value": "USD", "confidence": 0.9},
        "date": {"value": "2026-05-01", "confidence": 0.9},
        "category": {"value": "food", "confidence": 0.8},
        "payment_method": {"value": "cash", "confidence": 0.9},
        "tax": {"value": None, "confidence": 0.0},
        "discount": {"value": None, "confidence": 0.0},
        "transaction_ref": {"value": None, "confidence": 0.0},
        "payment_status": {"value": None, "confidence": 0.0},
        "warnings": [],
    })
    # Queue invalid output first, then valid output
    provider = FakeProvider(responses=["I am an AI, here is your receipt: {not json}", valid_json])
    app.dependency_overrides[get_provider] = lambda: provider

    files = {"image": ("receipt.jpg", sample_jpeg_bytes, "image/jpeg")}
    headers = {"X-App-Token": test_token}

    resp = client.post("/v1/extract", files=files, data={"hint": "receipt"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["fields"]["merchant"]["value"] == "Retry Bakery"
    assert provider.call_count == 2


def test_extract_invalid_json_twice_422(client, sample_jpeg_bytes, test_token):
    """When both model responses are malformed JSON, return 422."""
    provider = FakeProvider(responses=["not json 1", "not json 2"])
    app.dependency_overrides[get_provider] = lambda: provider

    files = {"image": ("receipt.jpg", sample_jpeg_bytes, "image/jpeg")}
    headers = {"X-App-Token": test_token}

    resp = client.post("/v1/extract", files=files, data={"hint": "receipt"}, headers=headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_output"
    assert resp.json()["error"]["retryable"] is False
    assert provider.call_count == 2


def test_extract_readable_false(client, sample_jpeg_bytes, test_token):
    """When image is blurry / not a receipt, return 200 with readable:false and null fields."""
    unreadable_json = json.dumps({
        "readable": False,
        "document_type": "unknown",
        "merchant": {"value": None, "confidence": 0.0},
        "amount": {"value": None, "confidence": 0.0},
        "currency": {"value": None, "confidence": 0.0},
        "date": {"value": None, "confidence": 0.0},
        "category": {"value": None, "confidence": 0.0},
        "payment_method": {"value": None, "confidence": 0.0},
        "tax": {"value": None, "confidence": 0.0},
        "discount": {"value": None, "confidence": 0.0},
        "transaction_ref": {"value": None, "confidence": 0.0},
        "payment_status": {"value": None, "confidence": 0.0},
        "warnings": ["blurry"],
    })
    provider = FakeProvider(default_response=unreadable_json)
    app.dependency_overrides[get_provider] = lambda: provider

    files = {"image": ("blurry.jpg", sample_jpeg_bytes, "image/jpeg")}
    headers = {"X-App-Token": test_token}

    resp = client.post("/v1/extract", files=files, data={"hint": "auto"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["readable"] is False
    assert body["fields"]["merchant"]["value"] is None
    assert body["fields"]["amount"]["value"] is None
    assert "blurry" in body["warnings"]
