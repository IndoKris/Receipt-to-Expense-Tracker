"""Fake deterministic extraction provider for testing and development."""

import asyncio
import json
from typing import List, Optional


class FakeProvider:
    """Deterministic extraction provider returning configurable fixture JSON."""
    name: str = "fake"

    def __init__(
        self,
        default_response: Optional[str] = None,
        responses: Optional[List[str]] = None,
        error: Optional[Exception] = None,
        delay_s: float = 0.0,
    ):
        self.default_response = default_response
        self.responses: List[str] = list(responses or [])
        self.error = error
        self.delay_s = delay_s
        self.call_count = 0
        self.last_prompt: Optional[str] = None

    async def extract(self, image_jpeg: bytes, prompt: str) -> str:
        """Return deterministic JSON based on configuration or document type in prompt."""
        self.call_count += 1
        self.last_prompt = prompt

        if self.delay_s > 0:
            await asyncio.sleep(self.delay_s)

        if self.error is not None:
            raise self.error

        if self.responses:
            return self.responses.pop(0)

        if self.default_response is not None:
            return self.default_response

        # Check prompt for document type hint
        if "The image is expected to be a payment screenshot" in prompt:
            return json.dumps({
                "readable": True,
                "document_type": "payment_screenshot",
                "merchant": {"value": "Chai Point", "confidence": 0.91},
                "amount": {"value": "250.00", "confidence": 0.97},
                "currency": {"value": "INR", "confidence": 0.9},
                "date": {"value": "2026-10-12", "confidence": 0.9},
                "category": {"value": "food", "confidence": 0.8},
                "payment_method": {"value": "upi", "confidence": 0.95},
                "tax": {"value": None, "confidence": 0.0},
                "discount": {"value": None, "confidence": 0.0},
                "transaction_ref": {"value": "428193771204", "confidence": 0.9},
                "payment_status": {"value": "success", "confidence": 0.9},
                "warnings": ["status_unverified"],
            })
        else:
            return json.dumps({
                "readable": True,
                "document_type": "receipt",
                "merchant": {"value": "Corner Bakery", "confidence": 0.95},
                "amount": {"value": "15.50", "confidence": 0.98},
                "currency": {"value": "USD", "confidence": 0.95},
                "date": {"value": "2026-10-10", "confidence": 0.92},
                "category": {"value": "food", "confidence": 0.85},
                "payment_method": {"value": "card", "confidence": 0.9},
                "tax": {"value": "1.25", "confidence": 0.85},
                "discount": {"value": None, "confidence": 0.0},
                "transaction_ref": {"value": "INV-10293", "confidence": 0.88},
                "payment_status": {"value": None, "confidence": 0.0},
                "warnings": [],
            })
