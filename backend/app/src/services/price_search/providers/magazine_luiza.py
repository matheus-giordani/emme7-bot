"""Magazine Luiza price provider."""

from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Iterable
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

from ..models import PriceSearchError, PriceSearchResult
from ..utils import DEFAULT_HEADERS, format_brl, normalize_whitespace, to_decimal
from .base import BasePriceProvider

logger = logging.getLogger("price_search.magalu")


class MagazineLuizaPriceProvider(BasePriceProvider):
    """Scrape Magazine Luiza using the embedded Next.js state."""

    site_name = "Magazine Luiza"
    _search_url = "https://www.magazineluiza.com.br/busca/{query}/"

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
                f"HTTP {response.status_code} ao buscar no Magazine Luiza.",
            )

        if "Radware Bot Manager" in response.text:
            raise PriceSearchError(
                self.site_name,
                "A Magazine Luiza bloqueou o acesso automatizado (captcha).",
            )

        soup = BeautifulSoup(response.text, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            logger.info(
                "Sem dados estruturados do Magazine Luiza para o termo '%s'.",
                query,
            )
            return

        try:
            data = json.loads(script.string)
            products = data["props"]["pageProps"]["data"]["search"]["products"]
        except (KeyError, json.JSONDecodeError) as exc:
            raise PriceSearchError(
                self.site_name,
                "Estrutura inesperada retornada pelo Magazine Luiza.",
            ) from exc

        count = 0
        for product in products:
            title = normalize_whitespace(product.get("title") or "")
            if not title:
                continue

            price_info = product.get("price") or {}
            raw_value = price_info.get("price") or price_info.get("bestPrice")
            price_decimal = None
            if raw_value:
                try:
                    price_decimal = Decimal(str(raw_value))
                except (InvalidOperation, ValueError):
                    price_decimal = None
            price_text = format_brl(price_decimal)

            link_path = product.get("url") or product.get("path")
            if not link_path:
                continue

            link = urljoin("https://www.magazineluiza.com.br", link_path)
            yield PriceSearchResult(
                site=self.site_name,
                title=title,
                link=link,
                price_text=price_text,
                price_value=price_decimal or to_decimal(price_text),
            )
            count += 1
            if count >= max_results:
                break

        if count == 0:
            logger.info("Nenhum resultado encontrado no Magazine Luiza para '%s'.", query)
