"""ChatBot graph coordinating the sales agent."""

from typing import Any, Dict, List, Optional

from src.models.user_models import InternalMessageModel
from src.agents.sales_agent import agent_sales


class ChatBotGraph:
    """Graph between agents to produce a final message."""

    def __init__(self) -> None:
        """Initialize parameters."""
        pass

    def run(
        self,
        data: List[InternalMessageModel],
        chat_messages: List[Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Run the graph."""
        self._inject_context(context)
        llm_message: str = self._run_sales_agent(data, chat_messages)
        return llm_message

    def _run_sales_agent(
        self, data: List[InternalMessageModel], chat_messages: List[Any]
    ) -> str:
        list_messagem_usr = [d.content or "" for d in data]
        messagem_usr = " ".join(list_messagem_usr)
        llm_message: str = agent_sales.run(messagem_usr, chat_messages)
        return llm_message

    def _inject_context(self, context: Optional[Dict[str, Any]]) -> None:
        """Expose scheduling context to the agent tools via memory state."""
        state = agent_sales.memory.state
        if isinstance(state, dict):
            state.clear()
        else:  # pragma: no cover - defensive fallback
            agent_sales.memory.state = {}

        if context:
            agent_sales.memory.state.update(context)
