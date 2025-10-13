"""Base interface for summary-capable LLMs."""


class SummaryLLM:
    """Contract: implement summarize(dialog, max_chars)."""

    def summarize(self, dialog: list[dict[str, str]], max_chars: int = 800) -> str:
        """Return a condensed summary for the given dialog up to max_chars."""
        raise NotImplementedError
