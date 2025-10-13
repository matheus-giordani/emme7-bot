"""Lightweight in-memory conversation history and KV state for the Agent."""

from typing import Any

from src.agents.lib_agent.message import Message


class Memory:
    """Compose RAM history and KV state; optionally summarized downstream."""

    def __init__(self, max_messages: int = 40, autosummarize_after: int = 24) -> None:
        """Initialize memory with caps for message window and summarize threshold."""
        self.messages: list[Message] = []
        self.state: dict[str, Any] = {}
        self.max_messages = max_messages
        self._autosummarize_after = autosummarize_after

    def add(self, msg: Message) -> None:
        """Append a message to the in-memory history and trigger optional summarize."""
        self.messages.append(msg)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
        self._update_summary()

    def conversation_window(self) -> list[Message]:
        """Return the most recent messages limited to the configured window size."""
        return self.messages[-self.max_messages:]

    def _update_summary(self) -> None:
        """Summarize long histories into short context (override in subclasses)."""
        return None
