"""SQLAlchemy models for an optional DB-backed memory implementation."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class for memory models."""


class Conversation(Base):
    """Represents a logical conversation with optional summary and messages."""

    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    messages: Mapped[List["MessageRow"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    kvs: Mapped[List["KVRow"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class MessageRow(Base):
    """Single message row within a conversation."""

    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class KVRow(Base):
    """Key-value store entry associated with a conversation."""

    __tablename__ = "kv_state"
    __table_args__ = (UniqueConstraint("conversation_id", "k", name="uq_conv_k"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    k: Mapped[str] = mapped_column(String(255))
    v: Mapped[str] = mapped_column(Text)

    conversation: Mapped[Conversation] = relationship(back_populates="kvs")
