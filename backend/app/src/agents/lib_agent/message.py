"""Message structure used by the Agent conversation window."""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Optional

from pydantic import StringConstraints


@dataclass
class Message:
    """High-level chat message for the Agent conversation history."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    chat_id: Optional[int] = None
    content_link: Optional[str] = None
    type: Optional[Annotated[str, StringConstraints(max_length=8)]] = None
    sent_at: Optional[datetime] = None
    who_sent: Optional[Annotated[str, StringConstraints(max_length=3)]] = None
