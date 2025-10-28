"""Sales assistant agent configured with lead capture tools."""

from src.agents.lib_agent.agent import Agent
from src.agents.lib_agent.utils.context_profile_providers import (
    customer_context_provider,
    lead_context_provider,
    store_context_provider,
)
from src.agents.lib_agent.utils.context_time_provider import time_provider
from src.agents.lib_agent.utils.openai_llm import OpenAILLM
from src.agents.tools.lead_management import register_lead
from src.agents.tools.price_search import search_product_prices


agent_sales = Agent(
    name="sales",
    llm=OpenAILLM("gpt-4o-mini"),
    tools=[register_lead, search_product_prices],
    context_providers=[
        time_provider("America/Sao_Paulo"),
        customer_context_provider(),
        store_context_provider(),
        lead_context_provider(),
    ],
)
