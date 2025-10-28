"""Utilities shared by price search providers."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def to_decimal(price_text: str | None) -> Optional[Decimal]:
    """Best effort conversion from Brazilian price strings to Decimal."""
    if not price_text:
        return None

    cleaned = re.sub(r"[^\d,\.]", "", price_text)
    if not cleaned:
        return None

    comma_count = cleaned.count(",")
    dot_count = cleaned.count(".")

    if comma_count and dot_count:
        # Brazilian format usually uses dot for thousands and comma for decimals.
        normalized = cleaned.replace(".", "").replace(",", ".")
    elif comma_count:
        normalized = cleaned.replace(".", "").replace(",", ".")
    elif dot_count:
        # Distinguish between decimal separator and thousands separator.
        last_dot_pos = cleaned.rfind(".")
        decimals_len = len(cleaned) - last_dot_pos - 1
        if decimals_len != 3:
            normalized = cleaned.replace(",", "")
        else:
            normalized = cleaned.replace(".", "")
    else:
        normalized = cleaned
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None


def normalize_whitespace(value: str) -> str:
    """Collapse repeated spaces and newlines."""
    return re.sub(r"\s+", " ", value).strip()


def format_brl(value: Decimal | None) -> Optional[str]:
    """Format Decimal values using Brazilian currency notation."""
    if value is None:
        return None

    quantized = value.quantize(Decimal("0.01"))
    formatted = f"R$ {quantized:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
