"""High-level service that orchestrates price lookups."""

from __future__ import annotations

import logging
from typing import Iterable, List, Sequence

from .models import PriceSearchResponse
from .providers.amazon import AmazonPriceProvider
from .providers.americanas import AmericanasPriceProvider
from .providers.base import BasePriceProvider
from .providers.magazine_luiza import MagazineLuizaPriceProvider
from .providers.mercado_livre import MercadoLivrePriceProvider
from .utils import format_brl

logger = logging.getLogger("price_search.service")


class PriceSearchService:
    """Coordinate price lookups across multiple providers."""

    DEFAULT_RESULTS_PER_SITE = 3

    def __init__(self, providers: Sequence[BasePriceProvider] | None = None) -> None:
        self.providers: Sequence[BasePriceProvider] = providers or (
            AmazonPriceProvider(),
            MercadoLivrePriceProvider(),
            AmericanasPriceProvider(),
            MagazineLuizaPriceProvider(),
        )

    def search(
        self,
        query: str,
        max_results_per_site: int | None = None,
    ) -> List[PriceSearchResponse]:
        """Execute price search across all providers."""
        limit = max_results_per_site or self.DEFAULT_RESULTS_PER_SITE
        responses: List[PriceSearchResponse] = []
        for provider in self.providers:
            response = provider.search(query, limit)
            responses.append(response)
        return responses

    def render_summary(
        self,
        query: str,
        responses: Iterable[PriceSearchResponse],
    ) -> str:
        """Turn provider responses into a WhatsApp friendly message."""
        lines: List[str] = []
        lines.append(f'Encontrei estas ofertas para "{query}":')
        lines.append("")

        for response in responses:
            lines.append(response.site)
            if response.error:
                lines.append(f"- {response.error}")
            elif not response.results:
                lines.append("- Nenhum produto encontrado.")
            else:
                for result in response.results:
                    price = (
                        result.price_text
                        or format_brl(result.price_value)
                        or "Preço indisponível"
                    )
                    if price:
                        lines.append(f"- {result.title} ({price}) – {result.link}")
                    else:
                        lines.append(f"- {result.title} – {result.link}")
            lines.append("")

        lines.append("Se quiser, posso procurar outro produto pra você.")
        message = "\n".join(lines).strip()
        logger.debug("Resumo de preços gerado: %s", message)
        return message
