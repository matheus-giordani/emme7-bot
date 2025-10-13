"""Generate conversation summaries using OpenAI Chat API."""

import os
from typing import Optional

from openai import OpenAI as _OpenAIClient

from src.agents.lib_agent.base_summary import SummaryLLM


class SummaryOpenAI(SummaryLLM):
    """Summarize a dialog with a single, short OpenAI Chat call."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        temperature: float = 0.2,
    ) -> None:
        """Initialize client, model and generation temperature.

        Args:
            model: OpenAI model name to use.
            api_key: API key (defaults to env OPENAI_API_KEY).
            temperature: Sampling temperature for the summary call.
        """
        self.client = _OpenAIClient(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.temperature = temperature

    def summarize(self, dialog: list[dict[str, str]], max_chars: int = 800) -> str:
        """Return a concise summary; truncate input for efficiency."""
        # Compacta diálogo bruto (apenas user/assistant) para não enviar gigante
        joined: list[str] = []
        total = 0
        for m in dialog:
            if m.get("role") in ("user", "assistant"):
                line = f"{m['role'].upper()}: {(m.get('content') or '').strip()}"
                total += len(line)
                joined.append(line)
                if total > max_chars:
                    break
        raw = "\n".join(joined)

        sys = "Você é um assistente que escreve resumos objetivos, claros e curtos."
        user = (
            "Resuma a conversa em até 120 palavras. Foque em:\n"
            "- objetivo do usuário;\n- dados fornecidos (nome, telefone, datas/horas);\n"
            "- decisões já tomadas;\n- próximas ações/pendências.\n\nCONVERSA:\n" + raw
        )
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
