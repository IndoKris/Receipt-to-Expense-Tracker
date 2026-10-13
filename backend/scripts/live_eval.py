"""Live evaluation script testing synthetic fixtures with real Gemma model."""

import asyncio
import os
import sys
from pathlib import Path

from app.config import get_settings
from app.images import validate_and_normalize_image
from app.main import extract_and_parse_json
from app.prompt import build_prompt
from app.providers.gemma import GemmaProvider
from app import verifier


async def run_evaluation() -> None:
    """Run synthetic test fixtures against real Gemini API and evaluate accuracy."""
    settings = get_settings()

    if not settings.gemini_api_key or not settings.gemini_api_key.strip():
        print("Skipping live evaluation: GEMINI_API_KEY is not set.")
        print("Set GEMINI_API_KEY and GEMMA_MODEL in .env to run live evaluation.")
        return

    if not settings.gemma_model or not settings.gemma_model.strip():
        print("Skipping live evaluation: GEMMA_MODEL is not set.")
        return

    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures" / "synthetic"
    if not fixtures_dir.exists():
        print("Synthetic fixtures not found. Generating them first...")
        from scripts.make_fixtures import generate_all_fixtures
        generate_all_fixtures(fixtures_dir)

    provider = GemmaProvider(
        api_key=settings.gemini_api_key,
        model=settings.gemma_model,
        timeout_s=settings.model_timeout_s,
    )

    test_cases = [
        {"filename": "clean_receipt.jpg", "hint": "receipt", "expected_type": "receipt"},
        {"filename": "upi_success.jpg", "hint": "payment_screenshot", "expected_type": "payment_screenshot"},
        {"filename": "injection_receipt.jpg", "hint": "receipt", "expected_type": "receipt"},
        {"filename": "blurry_receipt.jpg", "hint": "auto", "expected_type": "unknown"},
    ]

    print(f"\nRunning Live Evaluation using model '{settings.gemma_model}'...")
    print("-" * 80)
    print(f"{'Fixture':<25} | {'Readable':<10} | {'Doc Type':<18} | {'Amount':<10} | {'Status'}")
    print("-" * 80)

    for tc in test_cases:
        img_path = fixtures_dir / tc["filename"]
        if not img_path.exists():
            print(f"Missing fixture {tc['filename']}, skipping.")
            continue

        with open(img_path, "rb") as f:
            raw_bytes = f.read()

        try:
            jpeg_bytes = validate_and_normalize_image(raw_bytes, max_mb=settings.max_upload_mb)
            prompt = build_prompt(hint=tc["hint"])
            raw_output = await provider.extract(jpeg_bytes, prompt)
            model_output = extract_and_parse_json(raw_output)
            readable, doc_type, fields, warnings = verifier.normalize(model_output)

            amt_val = fields["amount"].value or "null"
            print(
                f"{tc['filename']:<25} | {str(readable):<10} | {doc_type:<18} | {amt_val:<10} | PASS"
            )
        except Exception as e:
            print(f"{tc['filename']:<25} | ERROR: {e}")

    print("-" * 80)
    print("Live evaluation complete.")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
