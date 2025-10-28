"""Amazon Brasil price provider."""

from __future__ import annotations

import logging
from typing import Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..models import PriceSearchError, PriceSearchResult
from ..utils import DEFAULT_HEADERS, normalize_whitespace, to_decimal
from .base import BasePriceProvider

logger = logging.getLogger("price_search.amazon")


class AmazonPriceProvider(BasePriceProvider):
    """Scrape Amazon search results."""

    site_name = "Amazon"
    _search_url = "https://www.amazon.com.br/s"

    def _search_impl(
        self,
        query: str,
        max_results: int,
    ) -> Iterable[PriceSearchResult]:
        headers = {
            **DEFAULT_HEADERS,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
                "image/webp,*/*;q=0.8"
            ),
            "Connection": "keep-alive",
        }
        response = requests.get(
            self._search_url,
            params={"k": query},
            headers=headers,
            timeout=15,
        )

        if response.status_code != 200:
            raise PriceSearchError(
                self.site_name,
                f"HTTP {response.status_code} ao buscar na Amazon.",
            )

        if "automated access" in response.text.lower():
            raise PriceSearchError(
                self.site_name,
                "A Amazon bloqueou o acesso automático. Tente novamente em instantes.",
            )

        soup = BeautifulSoup(response.text, "html.parser")
        results = soup.select('div[data-component-type="s-search-result"]')
        count = 0
        for item in results:
            title_tag = item.select_one("h2 a span")
            link_tag = item.select_one("h2 a")
            price_tag = item.select_one("span.a-price > span.a-offscreen")
            if not title_tag or not link_tag:
                continue

            title = normalize_whitespace(title_tag.get_text(strip=True))
            link = urljoin("https://www.amazon.com.br", link_tag["href"])
            price_text = price_tag.get_text(strip=True) if price_tag else None
            yield PriceSearchResult(
                site=self.site_name,
                title=title,
                link=link,
                price_text=price_text,
                price_value=to_decimal(price_text),
            )
            count += 1
            if count >= max_results:
                break

        if count == 0:
            logger.info("Nenhum resultado encontrado na Amazon para '%s'.", query)

