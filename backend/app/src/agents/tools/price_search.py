"""Tools for searching product prices across multiple marketplaces."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field, conint

from src.agents.lib_agent.tool import ToolContext, tool
from src.services.price_search.service import PriceSearchService
from src.services.price_search.utils import format_brl


class PriceSearchInput(BaseModel):
    """Arguments for the price search tool."""

    query: str = Field(..., description="Nome ou descrição do produto a pesquisar")
    max_results: conint(ge=1, le=10) = Field(3, description="Quantidade máxima de ofertas por site")


@tool(
    name="search_product_prices",
    description=(
        "Consulta simultaneamente marketplaces (Amazon, Mercado Livre, Americanas, "
        "Magazine Luiza) e retorna as ofertas mais relevantes para o produto informado."
    ),
    schema=PriceSearchInput,
)
def search_product_prices(args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    """Return structured pricing data for the requested product."""

    payload = PriceSearchInput(**args)
    service = PriceSearchService()
    responses = service.search(payload.query, payload.max_results)

    providers: List[Dict[str, Any]] = []
    for response in responses:
        provider_entry: Dict[str, Any] = {
            "site": response.site,
            "status": "error" if response.error else "ok",
        }
        if response.error:
            provider_entry["error"] = response.error
        else:
            provider_entry["results"] = [
                {
                    "title": result.title,
                    "price": result.price_text
                    or format_brl(result.price_value)
                    or "Preço indisponível",
                    "link": result.link,
                }
                for result in response.results
            ]
            if not provider_entry["results"]:
                provider_entry["message"] = "Nenhum produto encontrado"
        providers.append(provider_entry)

    state = ctx.memory.state
    if isinstance(state, dict):
        history = state.setdefault("price_search_history", [])
        if isinstance(history, list):
            history.append(
                {
                    "query": payload.query,
                    "providers": providers,
                }
            )

    return {
        "query": payload.query,
        "providers": providers,
    }
