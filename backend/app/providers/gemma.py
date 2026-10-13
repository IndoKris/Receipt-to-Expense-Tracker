"""Gemma extraction provider using google-genai SDK."""

import asyncio
from typing import Optional
from google import genai
from google.genai import types

from app.providers.base import UpstreamError, UpstreamTimeoutError


class GemmaProvider:
    """Extraction provider backed by Google Gemini API / Gemma models."""
    name: str = "gemma"

    def __init__(self, api_key: str, model: str, timeout_s: float = 40.0):
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s
        self.client = genai.Client(api_key=api_key)

    async def extract(self, image_jpeg: bytes, prompt: str) -> str:
        """Call Gemini API generate_content with image and text prompt."""
        try:
            async def _generate() -> str:
                resp = await self.client.aio.models.generate_content(
                    model=self.model,
                    contents=[
                        types.Part.from_bytes(data=image_jpeg, mime_type="image/jpeg"),
                        prompt,
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=1024,
                    ),
                )
                return resp.text or ""

            return await asyncio.wait_for(_generate(), timeout=self.timeout_s)
        except asyncio.TimeoutError as e:
            raise UpstreamTimeoutError(f"Model call timed out after {self.timeout_s}s") from e
        except Exception as e:
            raise UpstreamError(f"Gemini API error: {str(e)}") from e
