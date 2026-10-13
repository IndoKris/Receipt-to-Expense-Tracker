"""Unit tests for pure verifier normalization and validation rules."""

from datetime import date, timedelta
from app.schemas import DocumentType, ModelOutput, RawField
from app.verifier import normalize


def make_model_output(**kwargs) -> ModelOutput:
    """Helper to construct ModelOutput with defaults."""
    default_data = {
        "readable": True,
        "document_type": DocumentType.RECEIPT,
        "merchant": RawField(value="Starbucks", confidence=0.9),
        "amount": RawField(value="150.00", confidence=0.9),
        "currency": RawField(value="INR", confidence=0.9),
        "date": RawField(value="2026-05-10", confidence=0.9),
        "category": RawField(value="food", confidence=0.9),
        "payment_method": RawField(value="upi", confidence=0.9),
        "tax": RawField(value=None, confidence=0.0),
        "discount": RawField(value=None, confidence=0.0),
        "transaction_ref": RawField(value="TXN12345", confidence=0.9),
        "payment_status": RawField(value=None, confidence=0.0),
        "warnings": [],
    }
    default_data.update(kwargs)
    return ModelOutput(**default_data)


class TestVerifierAmount:
    def test_amount_clean_digits(self):
        mo = make_model_output(amount=RawField(value="250.00", confidence=0.95))
        readable, doc_type, fields, warnings = normalize(mo)
        assert fields["amount"].value == "250.00"
        assert fields["amount"].needs_review is False
        assert "amount_invalid" not in warnings

    def test_amount_commas(self):
        mo = make_model_output(amount=RawField(value="1,234.50", confidence=0.95))
        readable, doc_type, fields, warnings = normalize(mo)
        assert fields["amount"].value == "1234.50"
        assert fields["amount"].needs_review is True  # verifier changed value

    def test_amount_symbols(self):
        mo = make_model_output(amount=RawField(value="₹1,234.50", confidence=0.95))
        readable, doc_type, fields, warnings = normalize(mo)
        assert fields["amount"].value == "1234.50"
        assert fields["amount"].needs_review is True

        mo_usd = make_model_output(
            currency=RawField(value="USD", confidence=0.95),
            amount=RawField(value="$ 99.99", confidence=0.95),
        )
        _, _, fields_usd, _ = normalize(mo_usd)
        assert fields_usd["amount"].value == "99.99"
        assert fields_usd["amount"].needs_review is True

    def test_amount_three_decimals_rounding(self):
        mo = make_model_output(amount=RawField(value="10.555", confidence=0.95))
        readable, doc_type, fields, warnings = normalize(mo)
        assert fields["amount"].value == "10.56"
        assert "amount_rounded" in warnings
        assert fields["amount"].needs_review is True

    def test_amount_jpy_zero_decimals(self):
        mo = make_model_output(
            currency=RawField(value="JPY", confidence=0.95),
            amount=RawField(value="1000.6", confidence=0.95),
        )
        readable, doc_type, fields, warnings = normalize(mo)
        assert fields["amount"].value == "1001"
        assert "amount_rounded" in warnings

    def test_amount_zero(self):
        mo = make_model_output(amount=RawField(value="0", confidence=0.95))
        readable, doc_type, fields, warnings = normalize(mo)
        assert fields["amount"].value is None
        assert "amount_invalid" in warnings
        assert fields["amount"].needs_review is True

    def test_amount_negative(self):
        mo = make_model_output(amount=RawField(value="-15.50", confidence=0.95))
        readable, doc_type, fields, warnings = normalize(mo)
        assert fields["amount"].value is None
        assert "amount_invalid" in warnings
        assert fields["amount"].needs_review is True

    def test_amount_huge(self):
        mo = make_model_output(amount=RawField(value="1000000001", confidence=0.95))
        readable, doc_type, fields, warnings = normalize(mo)
        assert fields["amount"].value is None
        assert "amount_invalid" in warnings
        assert fields["amount"].needs_review is True


class TestVerifierCurrency:
    def test_currency_allowlist(self):
        for code in ["INR", "USD", "EUR", "GBP", "AED", "SGD", "JPY", "AUD", "CAD"]:
            mo = make_model_output(currency=RawField(value=code, confidence=0.9))
            _, _, fields, warnings = normalize(mo)
            assert fields["currency"].value == code
            assert "currency_unknown" not in warnings

    def test_currency_lowercase_normalization(self):
        mo = make_model_output(currency=RawField(value="inr", confidence=0.9))
        _, _, fields, _ = normalize(mo)
        assert fields["currency"].value == "INR"
        assert fields["currency"].needs_review is True

    def test_currency_unknown(self):
        mo = make_model_output(currency=RawField(value="XYZ", confidence=0.9))
        _, _, fields, warnings = normalize(mo)
        assert fields["currency"].value is None
        assert "currency_unknown" in warnings
        assert fields["currency"].needs_review is True

    def test_currency_null(self):
        mo = make_model_output(currency=RawField(value=None, confidence=0.0))
        _, _, fields, _ = normalize(mo)
        assert fields["currency"].value is None
        assert fields["currency"].needs_review is True


class TestVerifierDate:
    def test_date_valid(self):
        mo = make_model_output(date=RawField(value="2026-05-15", confidence=0.9))
        _, _, fields, warnings = normalize(mo)
        assert fields["date"].value == "2026-05-15"
        assert "date_invalid" not in warnings

    def test_date_feb_30_invalid(self):
        mo = make_model_output(date=RawField(value="2026-02-30", confidence=0.9))
        _, _, fields, warnings = normalize(mo)
        assert fields["date"].value is None
        assert "date_invalid" in warnings
        assert fields["date"].needs_review is True

    def test_date_prior_to_2000(self):
        mo = make_model_output(date=RawField(value="1999-12-31", confidence=0.9))
        _, _, fields, warnings = normalize(mo)
        assert fields["date"].value is None
        assert "date_invalid" in warnings

    def test_date_future_beyond_tomorrow(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        mo = make_model_output(date=RawField(value=future, confidence=0.9))
        _, _, fields, warnings = normalize(mo)
        assert fields["date"].value is None
        assert "date_invalid" in warnings

    def test_date_tomorrow_allowed(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        mo = make_model_output(date=RawField(value=tomorrow, confidence=0.9))
        _, _, fields, warnings = normalize(mo)
        assert fields["date"].value == tomorrow
        assert "date_invalid" not in warnings

    def test_date_ambiguous_flag(self):
        mo = make_model_output(
            date=RawField(value="2026-04-03", confidence=0.95),
            warnings=["date_ambiguous"],
        )
        _, _, fields, _ = normalize(mo)
        assert fields["date"].needs_review is True


class TestVerifierTaxAndDiscount:
    def test_tax_valid_and_implausible(self):
        # Tax <= amount is valid
        mo_valid = make_model_output(
            amount=RawField(value="100.00", confidence=0.9),
            tax=RawField(value="18.00", confidence=0.9),
        )
        _, _, fields, warnings = normalize(mo_valid)
        assert fields["tax"].value == "18.00"
        assert "tax_implausible" not in warnings

        # Tax > amount is implausible
        mo_invalid = make_model_output(
            amount=RawField(value="100.00", confidence=0.9),
            tax=RawField(value="105.00", confidence=0.9),
        )
        _, _, fields_inv, warnings_inv = normalize(mo_invalid)
        assert fields_inv["tax"].value is None
        assert "tax_implausible" in warnings_inv
        assert fields_inv["tax"].needs_review is True

    def test_discount_valid_and_implausible(self):
        # Discount <= 10 * amount is valid
        mo_valid = make_model_output(
            amount=RawField(value="50.00", confidence=0.9),
            discount=RawField(value="20.00", confidence=0.9),
        )
        _, _, fields, warnings = normalize(mo_valid)
        assert fields["discount"].value == "20.00"
        assert "discount_implausible" not in warnings

        # Discount > 10 * amount is implausible
        mo_invalid = make_model_output(
            amount=RawField(value="50.00", confidence=0.9),
            discount=RawField(value="550.00", confidence=0.9),
        )
        _, _, fields_inv, warnings_inv = normalize(mo_invalid)
        assert fields_inv["discount"].value is None
        assert "discount_implausible" in warnings_inv

    def test_null_tax_and_discount_no_review(self):
        mo = make_model_output(
            tax=RawField(value=None, confidence=0.0),
            discount=RawField(value=None, confidence=0.0),
        )
        _, _, fields, _ = normalize(mo)
        assert fields["tax"].value is None
        assert fields["tax"].needs_review is False
        assert fields["discount"].value is None
        assert fields["discount"].needs_review is False


class TestVerifierCategory:
    def test_category_valid(self):
        mo = make_model_output(category=RawField(value="groceries", confidence=0.85))
        _, _, fields, _ = normalize(mo)
        assert fields["category"].value == "groceries"
        assert fields["category"].needs_review is False

    def test_category_invalid_fallback_other(self):
        mo = make_model_output(category=RawField(value="electronics", confidence=0.85))
        _, _, fields, _ = normalize(mo)
        assert fields["category"].value == "other"
        assert fields["category"].needs_review is True

    def test_category_null_fallback_other(self):
        mo = make_model_output(category=RawField(value=None, confidence=0.0))
        _, _, fields, _ = normalize(mo)
        assert fields["category"].value == "other"
        assert fields["category"].needs_review is True


class TestVerifierPaymentStatus:
    def test_payment_status_forced_null_for_receipts(self):
        mo = make_model_output(
            document_type=DocumentType.RECEIPT,
            payment_status=RawField(value="success", confidence=0.9),
        )
        _, _, fields, warnings = normalize(mo)
        assert fields["payment_status"].value is None
        assert fields["payment_status"].needs_review is False
        assert "status_unverified" not in warnings

    def test_payment_status_screenshot_with_unverified(self):
        mo = make_model_output(
            document_type=DocumentType.PAYMENT_SCREENSHOT,
            transaction_ref=RawField(value="428193771204", confidence=0.9),
            payment_status=RawField(value="success", confidence=0.9),
        )
        _, _, fields, warnings = normalize(mo)
        assert fields["payment_status"].value == "success"
        assert "status_unverified" in warnings
        assert "status_uncorroborated" not in warnings

    def test_payment_status_screenshot_uncorroborated(self):
        # Success status without transaction ref generates status_uncorroborated
        mo = make_model_output(
            document_type=DocumentType.PAYMENT_SCREENSHOT,
            transaction_ref=RawField(value=None, confidence=0.0),
            payment_status=RawField(value="success", confidence=0.9),
        )
        _, _, fields, warnings = normalize(mo)
        assert fields["payment_status"].value == "success"
        assert "status_unverified" in warnings
        assert "status_uncorroborated" in warnings


class TestVerifierNeedsReviewThresholds:
    def test_amount_threshold_0_85(self):
        # 0.84 -> needs review
        mo_low = make_model_output(amount=RawField(value="100.00", confidence=0.84))
        _, _, fields_low, _ = normalize(mo_low)
        assert fields_low["amount"].needs_review is True

        # 0.86 -> no review needed
        mo_high = make_model_output(amount=RawField(value="100.00", confidence=0.86))
        _, _, fields_high, _ = normalize(mo_high)
        assert fields_high["amount"].needs_review is False

    def test_date_threshold_0_85(self):
        mo_low = make_model_output(date=RawField(value="2026-05-10", confidence=0.84))
        _, _, fields_low, _ = normalize(mo_low)
        assert fields_low["date"].needs_review is True

        mo_high = make_model_output(date=RawField(value="2026-05-10", confidence=0.86))
        _, _, fields_high, _ = normalize(mo_high)
        assert fields_high["date"].needs_review is False

    def test_merchant_threshold_0_75(self):
        mo_low = make_model_output(merchant=RawField(value="Corner Cafe", confidence=0.74))
        _, _, fields_low, _ = normalize(mo_low)
        assert fields_low["merchant"].needs_review is True

        mo_high = make_model_output(merchant=RawField(value="Corner Cafe", confidence=0.76))
        _, _, fields_high, _ = normalize(mo_high)
        assert fields_high["merchant"].needs_review is False


class TestVerifierStringSanitizationAndTruncation:
    def test_merchant_truncation_at_80(self):
        long_name = "A" * 100
        mo = make_model_output(merchant=RawField(value=long_name, confidence=0.9))
        _, _, fields, warnings = normalize(mo)
        assert len(fields["merchant"].value) == 80
        assert "truncated" in warnings
        assert fields["merchant"].needs_review is True

    def test_transaction_ref_truncation_at_64(self):
        long_ref = "R" * 80
        mo = make_model_output(transaction_ref=RawField(value=long_ref, confidence=0.9))
        _, _, fields, warnings = normalize(mo)
        assert len(fields["transaction_ref"].value) == 64
        assert "truncated" in warnings
        assert fields["transaction_ref"].needs_review is True

    def test_control_character_stripping_and_whitespace_collapse(self):
        dirty = "  Cafe\x00\x08   De   Paris \t\n  "
        mo = make_model_output(merchant=RawField(value=dirty, confidence=0.9))
        _, _, fields, _ = normalize(mo)
        assert fields["merchant"].value == "Cafe De Paris"


class TestVerifierReadable:
    def test_unreadable_when_model_says_false(self):
        mo = make_model_output(readable=False)
        readable, _, fields, _ = normalize(mo)
        assert readable is False
        for field in fields.values():
            assert field.value is None

    def test_unreadable_when_amount_and_merchant_both_null(self):
        mo = make_model_output(
            readable=True,
            amount=RawField(value=None, confidence=0.0),
            merchant=RawField(value=None, confidence=0.0),
        )
        readable, _, fields, _ = normalize(mo)
        assert readable is False
        assert fields["amount"].value is None
        assert fields["merchant"].value is None
