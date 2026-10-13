"""Pydantic schemas for API requests, responses, and model extraction."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentType(str, Enum):
    """Supported document types identified during extraction."""
    RECEIPT = "receipt"
    PAYMENT_SCREENSHOT = "payment_screenshot"
    UNKNOWN = "unknown"


class RawField(BaseModel):
    """Raw field extracted directly from the AI model output."""
    value: Optional[str] = None
    confidence: float = 0.0

    model_config = ConfigDict(extra="ignore")

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value_to_str(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        return str(v)

    @field_validator("confidence", mode="before")
    @classmethod
    def parse_confidence(cls, v: Any) -> float:
        if v is None:
            return 0.0
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0


class ModelOutput(BaseModel):
    """Raw extraction structure returned by Gemma or other LLM providers."""
    readable: bool = True
    document_type: DocumentType = DocumentType.UNKNOWN
    merchant: RawField = Field(default_factory=RawField)
    amount: RawField = Field(default_factory=RawField)
    currency: RawField = Field(default_factory=RawField)
    date: RawField = Field(default_factory=RawField)
    category: RawField = Field(default_factory=RawField)
    payment_method: RawField = Field(default_factory=RawField)
    tax: RawField = Field(default_factory=RawField)
    discount: RawField = Field(default_factory=RawField)
    transaction_ref: RawField = Field(default_factory=RawField)
    payment_status: RawField = Field(default_factory=RawField)
    warnings: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")

    @field_validator(
        "merchant",
        "amount",
        "currency",
        "date",
        "category",
        "payment_method",
        "tax",
        "discount",
        "transaction_ref",
        "payment_status",
        mode="before",
    )
    @classmethod
    def coerce_field_object(cls, v: Any) -> Any:
        if v is None:
            return RawField(value=None, confidence=0.0)
        if isinstance(v, (str, int, float, bool)):
            return RawField(value=str(v), confidence=0.0)
        return v


class FieldOutput(BaseModel):
    """Verified and normalized field value with confidence and review flag."""
    value: Optional[str] = None
    confidence: float = 0.0
    needs_review: bool = False

    model_config = ConfigDict(extra="ignore")


# FieldResponse is the API response field representation
FieldResponse = FieldOutput


class ExtractionResponse(BaseModel):
    """Full API response returned by /v1/extract."""
    request_id: str
    readable: bool
    document_type: str
    fields: Dict[str, FieldResponse]
    warnings: List[str] = Field(default_factory=list)
    model: str

    model_config = ConfigDict(extra="ignore")


class ErrorDetail(BaseModel):
    """Error object contained within an error response."""
    code: str
    message: str
    retryable: bool

    model_config = ConfigDict(extra="ignore")


class ErrorResponse(BaseModel):
    """Standardized error envelope across all API endpoints."""
    error: ErrorDetail

    model_config = ConfigDict(extra="ignore")
