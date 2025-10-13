"""Small context provider that injects local-time information as system message."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from zoneinfo import ZoneInfo
from ..base_context_providers import ContextProvider


def time_provider(tz: str = "America/Maceio") -> ContextProvider:
    """Return a provider callable that injects current local time for the user timezone."""

    def _provider(agent: Any, user_text: str) -> List[Dict[str, str]]:  # noqa: ARG001
        now = datetime.now(ZoneInfo(tz)).isoformat(timespec="seconds")
        return [
            {
                "role": "system",
                "content": (
                    f"Contexto temporal do usuário:\n- timezone: {tz}\n- agora_local: {now}\n"
                    "Interprete 'hoje/amanhã' usando esse relógio local e responda datas em YYYY-MM-DD."
                ),
            }
        ]

    return _provider
