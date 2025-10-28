"""Americanas price provider."""

from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Iterable, List, Optional
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

from ..models import PriceSearchError, PriceSearchResult
from ..utils import DEFAULT_HEADERS, format_brl, normalize_whitespace, to_decimal
from .base import BasePriceProvider

logger = logging.getLogger("price_search.americanas")


class AmericanasPriceProvider(BasePriceProvider):
    """Attempt to fetch offers from Americanas search results."""

    site_name = "Americanas"
    _search_url = "https://www.americanas.com.br/busca/{query}"

    def _search_impl(
        self,
        query: str,
        max_results: int,
    ) -> Iterable[PriceSearchResult]:
        encoded_query = quote_plus(query)
        url = self._search_url.format(query=encoded_query)
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)

        if response.status_code != 200:
            raise PriceSearchError(
                self.site_name,
                f"HTTP {response.status_code} ao buscar na Americanas.",
            )

        soup = BeautifulSoup(response.text, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            raise PriceSearchError(
                self.site_name,
                "Não foi possível ler os dados da Americanas.",
            )

        try:
            data = json.loads(script.string)
            products = self._extract_products(data)
        except (json.JSONDecodeError, KeyError) as exc:
            raise PriceSearchError(
                self.site_name,
                "Estrutura inesperada retornada pela Americanas.",
            ) from exc

        if not products:
            logger.info(
                "Nenhum produto retornado pela Americanas para o termo '%s'.", query
            )
            return

        for product in products[:max_results]:
            title = normalize_whitespace(product.get("name") or product.get("title") or "")
            if not title:
                continue

            price_text = product.get("priceText")
            price_value = to_decimal(price_text)

            link = product.get("link")
            if not link:
                continue
            absolute_link = urljoin("https://www.americanas.com.br", link)

            yield PriceSearchResult(
                site=self.site_name,
                title=title,
                link=absolute_link,
                price_text=price_text or format_brl(price_value),
                price_value=price_value,
            )

    def _extract_products(self, data: dict) -> List[dict]:
        """Best effort extraction of products from Americanas NEXT data."""
        sections: List[dict] = data["props"]["pageProps"]["page"].get("sections", [])
        sections += data["props"]["pageProps"].get("globalSections", {}).get(
            "sections", []
        )
        for section in sections:
            data_section = section.get("data") or {}
            # Some layouts expose products inside a nested collection dict.
            collection = data_section.get("collection")
            if isinstance(collection, dict) and "products" in collection:
                return self._normalize_products(collection["products"])

            # Others store products directly under 'items' or 'products'.
            for key in ("products", "items"):
                if key in data_section and isinstance(data_section[key], list):
                    return self._normalize_products(data_section[key])

        return []

    def _normalize_products(self, raw_products: List[dict]) -> List[dict]:
        """Normalize different Americanas structures to a common schema."""
        normalized: List[dict] = []
        for raw in raw_products:
            product = raw.get("product") if isinstance(raw, dict) else None
            entry = product or raw
            if not isinstance(entry, dict):
                continue

            sku = entry.get("sku") if isinstance(entry.get("sku"), dict) else {}
            sellers = sku.get("sellers") if isinstance(sku, dict) else []
            price_text: Optional[str] = None
            price_decimal: Optional[Decimal] = None

            if sellers and isinstance(sellers, list):
                offer = (
                    sellers[0].get("commertialOffer")
                    if isinstance(sellers[0], dict)
                    else None
                )
                if offer and offer.get("Price") is not None:
                    try:
                        price_decimal = Decimal(str(offer["Price"]))
                    except (InvalidOperation, ValueError):
                        price_decimal = None

            if price_decimal is None:
                raw_price = entry.get("price")
                if raw_price is not None:
                    try:
                        price_decimal = Decimal(str(raw_price))
                    except (InvalidOperation, ValueError):
                        price_decimal = to_decimal(str(raw_price))

            price_text = format_brl(price_decimal)

            normalized.append(
                {
                    "title": entry.get("name"),
                    "name": entry.get("name"),
                    "link": entry.get("link"),
                    "priceText": price_text,
                }
            )
        return normalized
