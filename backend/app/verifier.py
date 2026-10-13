"""Pure normalization and validation logic for extracted receipt data."""

import math
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas import DocumentType, FieldOutput, ModelOutput

# Supported categories
VALID_CATEGORIES: Set[str] = {
    "food",
    "groceries",
    "transport",
    "shopping",
    "bills",
    "health",
    "education",
    "other",
}

# Supported currencies
VALID_CURRENCIES: Set[str] = {
    "INR",
    "USD",
    "EUR",
    "GBP",
    "AED",
    "SGD",
    "JPY",
    "AUD",
    "CAD",
}

# Currency exponent map
CURRENCY_EXPONENTS: Dict[str, int] = {
    "INR": 2,
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "AED": 2,
    "SGD": 2,
    "JPY": 0,
    "AUD": 2,
    "CAD": 2,
}

# Supported payment methods
VALID_PAYMENT_METHODS: Set[str] = {
    "upi",
    "card",
    "cash",
    "netbanking",
    "wallet",
    "other",
}

# Supported screenshot payment statuses
VALID_PAYMENT_STATUSES: Set[str] = {
    "success",
    "pending",
    "failed",
    "unknown",
}

MAX_AMOUNT: Decimal = Decimal("1000000000")
MIN_DATE: date = date(2000, 1, 1)


def clamp_confidence(val: Any) -> float:
    """Clamp confidence score to [0.0, 1.0]."""
    if val is None:
        return 0.0
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return max(0.0, min(1.0, f))
    except (ValueError, TypeError):
        return 0.0


def sanitize_string(
    val: Optional[str],
    max_length: Optional[int] = None,
) -> Tuple[Optional[str], bool, bool]:
    """
    Unicode NFKC normalize, strip control chars, collapse whitespace, trim.
    Returns: (cleaned_string, was_truncated, was_changed)
    """
    if val is None:
        return None, False, False

    raw = str(val)
    # 1. NFKC normalize
    normalized = unicodedata.normalize("NFKC", raw)

    # 2. Strip control characters (keep standard whitespace to be collapsed)
    chars = []
    for ch in normalized:
        if ch in ("\n", "\r", "\t", " ") or not unicodedata.category(ch).startswith("C"):
            chars.append(ch)
    cleaned = "".join(chars)

    # 3. Collapse whitespace and trim
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        return None, False, True if raw != "" else False

    was_truncated = False
    if max_length is not None and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
        was_truncated = True

    was_changed = (cleaned != raw)
    return cleaned, was_truncated, was_changed


def parse_and_validate_amount(
    raw_amount: Optional[str],
    currency: Optional[str],
) -> Tuple[Optional[str], Optional[Decimal], List[str], bool]:
    """
    Parse amount as Decimal from digits and '.' only.
    Returns: (formatted_amount_str, decimal_value, warnings, was_changed)
    """
    warnings: List[str] = []
    if raw_amount is None:
        return None, None, warnings, False

    raw_str = str(raw_amount).strip()
    if not raw_str:
        warnings.append("amount_invalid")
        return None, None, warnings, True

    # Check for negative signs
    if "-" in raw_str:
        warnings.append("amount_invalid")
        return None, None, warnings, True

    # Clean commas and currency symbols
    # Strip common thousands separators and symbols
    cleaned = raw_str.replace(",", "").strip()
    cleaned = re.sub(r"[^\d.]", "", cleaned)

    if not cleaned or cleaned.count(".") > 1:
        warnings.append("amount_invalid")
        return None, None, warnings, True

    try:
        dec = Decimal(cleaned)
    except InvalidOperation:
        warnings.append("amount_invalid")
        return None, None, warnings, True

    # Must be > 0 and <= 1,000,000,000
    if dec <= 0 or dec > MAX_AMOUNT:
        warnings.append("amount_invalid")
        return None, None, warnings, True

    # Check exponent / decimal places
    exponent = CURRENCY_EXPONENTS.get(currency.upper() if currency else "INR", 2)
    # Determine number of decimal places
    tuple_exp = dec.as_tuple().exponent
    num_decimals = -tuple_exp if isinstance(tuple_exp, int) and tuple_exp < 0 else 0

    was_rounded = False
    if num_decimals > exponent:
        # Round half-up
        quantize_pattern = Decimal("1") if exponent == 0 else Decimal("0." + "0" * (exponent - 1) + "1")
        dec = dec.quantize(quantize_pattern, rounding=ROUND_HALF_UP)
        warnings.append("amount_rounded")
        was_rounded = True

    # Format output string
    if exponent == 0:
        formatted_str = f"{dec:.0f}"
    else:
        formatted_str = f"{dec:.{exponent}f}"

    was_changed = (formatted_str != raw_str) or was_rounded
    return formatted_str, dec, warnings, was_changed


def parse_and_validate_date(
    raw_date: Optional[str],
) -> Tuple[Optional[str], List[str], bool]:
    """
    Validate strict YYYY-MM-DD real calendar date between 2000-01-01 and today+1.
    Returns: (date_str, warnings, was_changed)
    """
    warnings: List[str] = []
    if raw_date is None:
        return None, warnings, False

    raw_str = str(raw_date).strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", raw_str):
        warnings.append("date_invalid")
        return None, warnings, True

    try:
        parsed_dt = datetime.strptime(raw_str, "%Y-%m-%d").date()
    except ValueError:
        warnings.append("date_invalid")
        return None, warnings, True

    max_date = date.today() + timedelta(days=1)
    if parsed_dt < MIN_DATE or parsed_dt > max_date:
        warnings.append("date_invalid")
        return None, warnings, True

    return raw_str, warnings, False


def parse_and_validate_tax_discount(
    raw_val: Optional[str],
    amount_dec: Optional[Decimal],
    field_name: str,
    currency: Optional[str],
) -> Tuple[Optional[str], List[str], bool]:
    """
    Parse tax or discount as Decimal >= 0.
    tax <= amount; discount <= 10 * amount.
    Returns: (formatted_str, warnings, was_changed)
    """
    warnings: List[str] = []
    if raw_val is None:
        return None, warnings, False

    raw_str = str(raw_val).strip()
    if not raw_str:
        return None, warnings, True

    cleaned = raw_str.replace(",", "").strip()
    cleaned = re.sub(r"[^\d.]", "", cleaned)

    if "-" in raw_str or not cleaned or cleaned.count(".") > 1:
        warnings.append(f"{field_name}_implausible")
        return None, warnings, True

    try:
        dec = Decimal(cleaned)
    except InvalidOperation:
        warnings.append(f"{field_name}_implausible")
        return None, warnings, True

    if dec < 0:
        warnings.append(f"{field_name}_implausible")
        return None, warnings, True

    if amount_dec is not None:
        if field_name == "tax" and dec > amount_dec:
            warnings.append("tax_implausible")
            return None, warnings, True
        if field_name == "discount" and dec > (Decimal("10") * amount_dec):
            warnings.append("discount_implausible")
            return None, warnings, True

    exponent = CURRENCY_EXPONENTS.get(currency.upper() if currency else "INR", 2)
    if exponent == 0:
        formatted_str = f"{dec:.0f}"
    else:
        formatted_str = f"{dec:.{exponent}f}"

    was_changed = (formatted_str != raw_str)
    return formatted_str, warnings, was_changed


def normalize(model_output: ModelOutput) -> Tuple[bool, str, Dict[str, FieldOutput], List[str]]:
    """
    Pure verifier function implementing all rules from TRD §4.5.
    Returns: (readable, document_type, fields_dict, warnings)
    """
    warnings: List[str] = list(model_output.warnings or [])
    doc_type = model_output.document_type.value

    # --- 1. Currency ---
    raw_curr = model_output.currency.value
    curr_conf = clamp_confidence(model_output.currency.confidence)
    curr_val: Optional[str] = None
    curr_changed = False

    if raw_curr is not None:
        cleaned_curr = raw_curr.strip().upper()
        if cleaned_curr in VALID_CURRENCIES:
            curr_val = cleaned_curr
            curr_changed = (raw_curr != curr_val)
        else:
            warnings.append("currency_unknown")
            curr_changed = True
    else:
        curr_changed = False

    curr_needs_review = (curr_val is None) or (curr_conf < 0.75) or curr_changed

    # --- 2. Merchant ---
    raw_merch = model_output.merchant.value
    merch_conf = clamp_confidence(model_output.merchant.confidence)
    merch_val, merch_trunc, merch_changed = sanitize_string(raw_merch, max_length=80)
    if merch_trunc:
        warnings.append("truncated")
        merch_changed = True

    merch_needs_review = (merch_val is None) or (merch_conf < 0.75) or merch_changed

    # --- 3. Amount ---
    raw_amt = model_output.amount.value
    amt_conf = clamp_confidence(model_output.amount.confidence)
    amt_val, amt_dec, amt_warns, amt_changed = parse_and_validate_amount(raw_amt, curr_val)
    warnings.extend(amt_warns)

    # For amount: threshold is 0.85
    amt_needs_review = (amt_val is None) or (amt_conf < 0.85) or amt_changed

    # --- 4. Date ---
    raw_date = model_output.date.value
    date_conf = clamp_confidence(model_output.date.confidence)
    date_val, date_warns, date_changed = parse_and_validate_date(raw_date)
    warnings.extend(date_warns)

    is_date_ambiguous = "date_ambiguous" in warnings
    # For date: threshold is 0.85
    date_needs_review = (
        (date_val is None)
        or (date_conf < 0.85)
        or is_date_ambiguous
        or date_changed
    )

    # --- 5. Category ---
    raw_cat = model_output.category.value
    cat_conf = clamp_confidence(model_output.category.confidence)
    cat_changed = False
    if raw_cat is not None:
        norm_cat = raw_cat.strip().lower()
        if norm_cat in VALID_CATEGORIES:
            cat_val = norm_cat
            cat_changed = (raw_cat != norm_cat)
        else:
            cat_val = "other"
            cat_changed = True
    else:
        cat_val = "other"
        cat_changed = True

    cat_needs_review = cat_changed or (cat_conf < 0.75)

    # --- 6. Payment Method ---
    raw_pm = model_output.payment_method.value
    pm_conf = clamp_confidence(model_output.payment_method.confidence)
    pm_val: Optional[str] = None
    pm_changed = False

    if raw_pm is not None:
        norm_pm = raw_pm.strip().lower()
        if norm_pm in VALID_PAYMENT_METHODS:
            pm_val = norm_pm
            pm_changed = (raw_pm != norm_pm)
        else:
            pm_val = None
            pm_changed = True
            pm_conf = 0.0

    pm_needs_review = (pm_val is not None and pm_conf < 0.75) or pm_changed

    # --- 7. Tax & Discount ---
    raw_tax = model_output.tax.value
    tax_conf = clamp_confidence(model_output.tax.confidence)
    tax_val, tax_warns, tax_changed = parse_and_validate_tax_discount(raw_tax, amt_dec, "tax", curr_val)
    warnings.extend(tax_warns)
    tax_needs_review = tax_changed or (tax_val is not None and tax_conf < 0.75)

    raw_disc = model_output.discount.value
    disc_conf = clamp_confidence(model_output.discount.confidence)
    disc_val, disc_warns, disc_changed = parse_and_validate_tax_discount(
        raw_disc, amt_dec, "discount", curr_val
    )
    warnings.extend(disc_warns)
    disc_needs_review = disc_changed or (disc_val is not None and disc_conf < 0.75)

    # --- 8. Transaction Ref ---
    raw_ref = model_output.transaction_ref.value
    ref_conf = clamp_confidence(model_output.transaction_ref.confidence)
    ref_val, ref_trunc, ref_changed = sanitize_string(raw_ref, max_length=64)
    if ref_trunc:
        warnings.append("truncated")
        ref_changed = True

    ref_needs_review = (ref_val is not None and ref_conf < 0.75) or ref_changed

    # --- 9. Payment Status ---
    raw_status = model_output.payment_status.value
    status_conf = clamp_confidence(model_output.payment_status.confidence)
    status_val: Optional[str] = None
    status_needs_review = False

    if doc_type == DocumentType.RECEIPT.value:
        # Force null for receipts
        status_val = None
        status_conf = 0.0
        status_needs_review = False
    elif doc_type == DocumentType.PAYMENT_SCREENSHOT.value:
        if raw_status is not None:
            norm_status = raw_status.strip().lower()
            if norm_status in VALID_PAYMENT_STATUSES:
                status_val = norm_status
            else:
                status_val = "unknown"
                status_needs_review = True
        else:
            status_val = "unknown"
            status_needs_review = True

        # Add status_unverified whenever a status is present
        if status_val is not None:
            warnings.append("status_unverified")
            if status_val == "success" and not ref_val:
                warnings.append("status_uncorroborated")

        status_needs_review = status_needs_review or (status_conf < 0.75)
    else:
        # Unknown document type
        status_val = None
        status_conf = 0.0
        status_needs_review = False

    # --- 10. Readable determination ---
    # Readable: if model says false, or amount AND merchant are both null -> readable=false
    readable = bool(model_output.readable)
    if amt_val is None and merch_val is None:
        readable = False

    # Deduplicate warnings preserving order
    seen_warnings = set()
    deduped_warnings: List[str] = []
    for w in warnings:
        if w and w not in seen_warnings:
            seen_warnings.add(w)
            deduped_warnings.append(w)

    fields: Dict[str, FieldOutput] = {
        "merchant": FieldOutput(value=merch_val, confidence=merch_conf, needs_review=merch_needs_review),
        "amount": FieldOutput(value=amt_val, confidence=amt_conf, needs_review=amt_needs_review),
        "currency": FieldOutput(value=curr_val, confidence=curr_conf, needs_review=curr_needs_review),
        "date": FieldOutput(value=date_val, confidence=date_conf, needs_review=date_needs_review),
        "category": FieldOutput(value=cat_val, confidence=cat_conf, needs_review=cat_needs_review),
        "payment_method": FieldOutput(value=pm_val, confidence=pm_conf, needs_review=pm_needs_review),
        "tax": FieldOutput(value=tax_val, confidence=tax_conf, needs_review=tax_needs_review),
        "discount": FieldOutput(value=disc_val, confidence=disc_conf, needs_review=disc_needs_review),
        "transaction_ref": FieldOutput(value=ref_val, confidence=ref_conf, needs_review=ref_needs_review),
        "payment_status": FieldOutput(value=status_val, confidence=status_conf, needs_review=status_needs_review),
    }

    # If readable is false, null out all field values per TRD §4.3
    if not readable:
        for key in fields:
            fields[key] = FieldOutput(value=None, confidence=0.0, needs_review=False)

    return readable, doc_type, fields, deduped_warnings
