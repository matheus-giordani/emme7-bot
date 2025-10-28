"""Base classes for price search providers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Iterable

from ..models import PriceSearchError, PriceSearchResponse, PriceSearchResult

logger = logging.getLogger("price_search.provider")


class BasePriceProvider(ABC):
    """Common behaviour for scraping providers."""

    site_name: str

    def search(self, query: str, max_results: int = 3) -> PriceSearchResponse:
        """Public search entry point with error handling."""
        try:
            offers = list(self._search_impl(query, max_results))
            return PriceSearchResponse(site=self.site_name, results=offers)
        except PriceSearchError as exc:
            logger.warning(
                "Falha específica do provedor %s: %s", exc.site, exc.message
            )
            return PriceSearchResponse(site=self.site_name, error=exc.message)
        except Exception as exc:  # pragma: no cover - defensive path
            logger.exception("Erro inesperado ao buscar preços em %s", self.site_name)
            return PriceSearchResponse(
                site=self.site_name, error=f"Não foi possível acessar {self.site_name}."
            )

    @abstractmethod
    def _search_impl(
        self,
        query: str,
        max_results: int,
    ) -> Iterable[PriceSearchResult]:
        """Return raw offers for the given query."""
        raise NotImplementedError

