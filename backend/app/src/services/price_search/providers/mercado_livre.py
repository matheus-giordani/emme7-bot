"""Mercado Livre price provider."""

from __future__ import annotations

import logging
from typing import Iterable
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

from ..models import PriceSearchError, PriceSearchResult
from ..utils import DEFAULT_HEADERS, normalize_whitespace, to_decimal
from .base import BasePriceProvider

logger = logging.getLogger("price_search.mercadolivre")


class MercadoLivrePriceProvider(BasePriceProvider):
    """Scrape Mercado Livre Brasil."""

    site_name = "Mercado Livre"
    _search_url = "https://lista.mercadolivre.com.br/{query}"

    def _search_impl(
        self,
        query: str,
        max_results: int,
    ) -> Iterable[PriceSearchResult]:
        encoded_query = quote_plus(query)
        url = self._search_url.format(query=encoded_query)
        headers = {
            **DEFAULT_HEADERS,
            "Referer": "https://www.mercadolivre.com.br/",
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            raise PriceSearchError(
                self.site_name,
                f"HTTP {response.status_code} ao buscar no Mercado Livre.",
            )

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select("li.ui-search-layout__item")
        count = 0
        for item in items:
            title_anchor = item.select_one("a.poly-component__title")
            price_whole = item.select_one(".andes-money-amount__fraction")
            link = (
                title_anchor["href"]
                if title_anchor and title_anchor.has_attr("href")
                else None
            )
            if not title_anchor or not link:
                continue

            title = normalize_whitespace(title_anchor.get_text(strip=True))
            price_cents = item.select_one(".andes-money-amount__cents")
            price_text = None
            if price_whole:
                cents = price_cents.get_text(strip=True) if price_cents else None
                price_text = f"R$ {price_whole.get_text(strip=True)}"
                if cents:
                    price_text += f",{cents}"

            yield PriceSearchResult(
                site=self.site_name,
                title=title,
                link=urljoin("https://lista.mercadolivre.com.br", link),
                price_text=price_text,
                price_value=to_decimal(price_text),
            )
            count += 1
            if count >= max_results:
                break

        if count == 0:
            logger.info(
                "Nenhum resultado encontrado no Mercado Livre para '%s'.", query
            )

