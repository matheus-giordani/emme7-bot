"""Types for small context providers that inject system messages into the Agent."""

from __future__ import annotations

from typing import Any, Dict, List, Protocol


class ContextProvider(Protocol):
    """Callable protocol to provide system messages dynamically."""

    def __call__(self, agent: Any, user_text: str) -> List[Dict[str, str]]:
        """Return a list of system messages based on the user text and agent."""
        ...
