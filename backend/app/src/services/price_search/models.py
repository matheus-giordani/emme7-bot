"""Domain models for price search results."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional


@dataclass(slots=True)
class PriceSearchResult:
    """Single offer returned by a price provider."""

    site: str
    title: str
    link: str
    price_text: Optional[str] = None
    price_value: Optional[Decimal] = None


@dataclass(slots=True)
class PriceSearchResponse:
    """Aggregated result for a specific provider."""

    site: str
    results: List[PriceSearchResult] = field(default_factory=list)
    error: Optional[str] = None


class PriceSearchError(RuntimeError):
    """Raised when a provider cannot complete the search."""

    def __init__(self, site: str, message: str) -> None:
        super().__init__(message)
        self.site = site
        self.message = message

