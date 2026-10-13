"""Base extraction provider protocol and exceptions."""

from typing import Protocol


class UpstreamError(Exception):
    """Raised when upstream AI provider returns an error."""
    pass


class UpstreamTimeoutError(UpstreamError):
    """Raised when call to upstream AI provider times out."""
    pass


class ExtractionProvider(Protocol):
    """Protocol defining the interface for document extraction providers."""
    name: str

    async def extract(self, image_jpeg: bytes, prompt: str) -> str:
        """Extract text from the image given the system prompt."""
        ...
