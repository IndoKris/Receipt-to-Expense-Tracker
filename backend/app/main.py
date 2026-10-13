"""FastAPI application for Receipt-to-Expense Tracker extraction backend."""

import hmac
import json
import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import Depends, FastAPI, File, Form, Header, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.images import ImageTooLargeError, UnsupportedImageError, validate_and_normalize_image
from app.prompt import build_prompt, build_retry_prompt
from app.providers.base import ExtractionProvider, UpstreamError, UpstreamTimeoutError
from app.providers.fake import FakeProvider
from app.providers.gemma import GemmaProvider
from app.ratelimit import RateLimiter
from app.schemas import ErrorResponse, ExtractionResponse, ModelOutput
from app import verifier

# Configure structured logging without logging any image data or extracted PII
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("receipt_tracker")

# Global rate limiter initialized from settings
limiter: Optional[RateLimiter] = None


def get_rate_limiter(settings: Settings = Depends(get_settings)) -> RateLimiter:
    """Return shared rate limiter instance."""
    global limiter
    if limiter is None:
        limiter = RateLimiter(rate_per_min=settings.rate_limit_per_min)
    return limiter


def get_provider(settings: Settings = Depends(get_settings)) -> ExtractionProvider:
    """Dependency returning configured extraction provider."""
    provider_name = settings.provider.strip().lower()
    if provider_name == "fake":
        return FakeProvider()
    elif provider_name == "gemma":
        settings.validate_provider()
        return GemmaProvider(
            api_key=settings.gemini_api_key or "",
            model=settings.gemma_model or "",
            timeout_s=settings.model_timeout_s,
        )
    else:
        raise ValueError(f"Unknown provider '{settings.provider}'. Must be 'gemma' or 'fake'.")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Validate configuration on application startup."""
    settings = get_settings()
    global limiter
    limiter = RateLimiter(rate_per_min=settings.rate_limit_per_min)
    if settings.provider.strip().lower() == "gemma":
        settings.validate_provider()
    logger.info(f"App initialized. Provider: {settings.provider}")
    yield


app = FastAPI(
    title="Receipt-to-Expense Tracker Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for mobile app clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def make_error_response(
    status_code: int,
    code: str,
    message: str,
    retryable: bool,
    headers: Optional[Dict[str, str]] = None,
) -> JSONResponse:
    """Helper to generate standardized ErrorResponse format."""
    payload = {
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
        }
    }
    return JSONResponse(status_code=status_code, content=payload, headers=headers)


def extract_and_parse_json(raw_text: str) -> ModelOutput:
    """
    Strip code fences, extract outermost JSON object, and validate against ModelOutput.
    Raises ValueError on parse or schema validation failure.
    """
    text = (raw_text or "").strip()
    # Strip markdown code fences if present
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace == -1 or last_brace == -1 or last_brace < first_brace:
        raise ValueError("No JSON object braces found in model output")

    json_str = text[first_brace : last_brace + 1]
    parsed_dict = json.loads(json_str)
    return ModelOutput.model_validate(parsed_dict)


@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    """Liveness and health check endpoint."""
    return {"status": "ok"}


@app.post("/v1/extract", response_model=ExtractionResponse, responses={
    401: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    415: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
    504: {"model": ErrorResponse},
})
async def extract_receipt(
    request: Request,
    image: UploadFile = File(...),
    hint: str = Form(default="auto"),
    x_app_token: Optional[str] = Header(None, alias="X-App-Token"),
    settings: Settings = Depends(get_settings),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    provider: ExtractionProvider = Depends(get_provider),
) -> Any:
    """
    Extract expense details from an uploaded receipt or payment screenshot.
    """
    req_id = str(uuid.uuid4())
    start_time = time.monotonic()
    model_name = settings.gemma_model or getattr(provider, "name", "unknown")

    # 1. Auth check using constant-time comparison
    if not x_app_token or not hmac.compare_digest(
        x_app_token.encode("utf-8"), settings.app_token.encode("utf-8")
    ):
        latency_ms = (time.monotonic() - start_time) * 1000.0
        logger.warning(
            f"request_id={req_id} status=401 latency_ms={latency_ms:.1f} model={model_name} error=unauthorized"
        )
        return make_error_response(
            status_code=401,
            code="unauthorized",
            message="Invalid or missing X-App-Token header",
            retryable=False,
        )

    # 2. Rate limiting check
    client_ip = request.client.host if request.client else "127.0.0.1"
    allowed, retry_after = rate_limiter.check(client_ip)
    if not allowed:
        latency_ms = (time.monotonic() - start_time) * 1000.0
        logger.warning(
            f"request_id={req_id} status=429 latency_ms={latency_ms:.1f} model={model_name} error=rate_limited"
        )
        return make_error_response(
            status_code=429,
            code="rate_limited",
            message=f"Rate limit exceeded. Try again after {retry_after} seconds.",
            retryable=True,
            headers={"Retry-After": str(retry_after)},
        )

    # 3. Read upload and validate size cap
    max_bytes = settings.max_upload_mb * 1024 * 1024
    image_bytes = await image.read()
    if len(image_bytes) > max_bytes:
        latency_ms = (time.monotonic() - start_time) * 1000.0
        logger.warning(
            f"request_id={req_id} status=413 latency_ms={latency_ms:.1f} model={model_name} error=too_large"
        )
        return make_error_response(
            status_code=413,
            code="too_large",
            message=f"Image exceeds maximum upload limit of {settings.max_upload_mb} MB.",
            retryable=False,
        )

    # 4. Decode, verify, and normalize image with Pillow
    try:
        jpeg_bytes = validate_and_normalize_image(image_bytes, max_mb=settings.max_upload_mb)
    except ImageTooLargeError as e:
        latency_ms = (time.monotonic() - start_time) * 1000.0
        logger.warning(
            f"request_id={req_id} status=413 latency_ms={latency_ms:.1f} model={model_name} error=too_large"
        )
        return make_error_response(
            status_code=413,
            code="too_large",
            message=str(e),
            retryable=False,
        )
    except UnsupportedImageError as e:
        latency_ms = (time.monotonic() - start_time) * 1000.0
        logger.warning(
            f"request_id={req_id} status=415 latency_ms={latency_ms:.1f} model={model_name} error=unsupported"
        )
        return make_error_response(
            status_code=415,
            code="unsupported",
            message=str(e),
            retryable=False,
        )

    # 5. Build prompt
    prompt = build_prompt(hint=hint)

    # 6. Extract with provider
    raw_output: str
    try:
        raw_output = await provider.extract(jpeg_bytes, prompt)
    except UpstreamTimeoutError as e:
        latency_ms = (time.monotonic() - start_time) * 1000.0
        logger.error(
            f"request_id={req_id} status=504 latency_ms={latency_ms:.1f} model={model_name} error=upstream_timeout"
        )
        return make_error_response(
            status_code=504,
            code="upstream_timeout",
            message=str(e),
            retryable=True,
        )
    except UpstreamError as e:
        latency_ms = (time.monotonic() - start_time) * 1000.0
        logger.error(
            f"request_id={req_id} status=502 latency_ms={latency_ms:.1f} model={model_name} error=upstream_error"
        )
        return make_error_response(
            status_code=502,
            code="upstream_error",
            message=str(e),
            retryable=True,
        )

    # 7. Parse JSON with one retry if parsing fails
    model_output: ModelOutput
    try:
        model_output = extract_and_parse_json(raw_output)
    except Exception:
        # First attempt failed. Retry once with appended instruction prompt
        retry_prompt = build_retry_prompt(prompt)
        try:
            retry_raw = await provider.extract(jpeg_bytes, retry_prompt)
            model_output = extract_and_parse_json(retry_raw)
        except (UpstreamTimeoutError, UpstreamError) as e:
            status_code = 504 if isinstance(e, UpstreamTimeoutError) else 502
            code = "upstream_timeout" if isinstance(e, UpstreamTimeoutError) else "upstream_error"
            latency_ms = (time.monotonic() - start_time) * 1000.0
            logger.error(
                f"request_id={req_id} status={status_code} latency_ms={latency_ms:.1f} model={model_name} error={code}"
            )
            return make_error_response(
                status_code=status_code,
                code=code,
                message=str(e),
                retryable=True,
            )
        except Exception:
            latency_ms = (time.monotonic() - start_time) * 1000.0
            logger.warning(
                f"request_id={req_id} status=422 latency_ms={latency_ms:.1f} model={model_name} error=invalid_output"
            )
            return make_error_response(
                status_code=422,
                code="invalid_output",
                message="Model output could not be parsed as valid JSON matching schema after retry.",
                retryable=False,
            )

    # 8. Verifier normalization & business rules
    readable, document_type, fields, warnings = verifier.normalize(model_output)

    latency_ms = (time.monotonic() - start_time) * 1000.0
    logger.info(
        f"request_id={req_id} status=200 latency_ms={latency_ms:.1f} model={model_name} readable={readable}"
    )

    return ExtractionResponse(
        request_id=req_id,
        readable=readable,
        document_type=document_type,
        fields=fields,
        warnings=warnings,
        model=model_name,
    )
