"""DB-backed Memory implementation that persists and reads chat history."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.agents.lib_agent.base_memory import Memory
from src.agents.lib_agent.message import Message
from src.repositories.interactions.models.chats_messages_model import ChatsMessages
from src.repositories.interactions.models.chats_model import Chats

# mapeamentos de papel <-> who_sent
ROLE_TO_WHO = {"user": "usr", "assistant": "llm"}
WHO_TO_ROLE = {"usr": "user", "llm": "assistant"}


class DBMemory(Memory):
    """Memory backed by relational storage using SQLAlchemy models."""

    def __init__(
        self,
        engine: Engine,
        chat_id: int,
        max_messages: int = 400,
        autosummarize_after: int = 80,
    ):
        """Initialize with engine and chat_id to bind the conversation context."""
        super().__init__(
            max_messages=max_messages, autosummarize_after=autosummarize_after
        )
        self.engine = engine
        self.chat_id = chat_id

    # ---- histórico ----
    def add(self, msg: Message) -> None:
        """Persist user/assistant messages and maintain in-memory window."""
        if msg.role in ("user", "assistant"):
            who = ROLE_TO_WHO.get(msg.role, "llm")
            with Session(self.engine) as s:
                s.add(
                    ChatsMessages(
                        chat_id=self.chat_id,
                        content=msg.content or "",
                        content_link=None,
                        type="text",
                        sent_at=datetime.utcnow(),
                        who_sent=who,
                    )
                )
                chat = s.get(Chats, self.chat_id)
                if chat:
                    chat.last_interacted_at = datetime.utcnow()
                s.commit()
        # pequena janela em RAM (opcional; não impacta schema)
        super().add(msg)

    def conversation_window(self) -> list[Message]:
        """Return last messages up to max_messages in chronological order."""
        with Session(self.engine) as s:
            rows = s.scalars(
                select(ChatsMessages)
                .where(ChatsMessages.chat_id == self.chat_id)
                .order_by(ChatsMessages.sent_at.desc(), ChatsMessages.id.desc())
                .limit(self.max_messages)
            ).all()
        rows = list(reversed(rows))
        msgs: list[Message] = []
        for r in rows:
            # só mensagens de texto "normais"; ignora anexos e resumos antigos
            if r.type != "text":
                continue
            role = WHO_TO_ROLE.get(r.who_sent, "assistant")
            msgs.append(Message(role=role, content=r.content))
        return msgs
