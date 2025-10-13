"""This module defines the Message model for storing messages in the database."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    TIMESTAMP,
    Text,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from src.repositories.interactions.database import Base


class ChatsMessages(Base):  # type: ignore
    """
    Represents a chat message entity in the database.

    Attributes:
        id (int): Primary key, unique identifier for the message.
        chat_id (int): ID of the chat.
        content (str): The text content of the message.
        content_link (str): Link associated with the message (if it is an audio, image, video...)
        type (str): The type of the message ("text", "image", "audio", "video", "document").
        sent_at (timestamp): When the message was received.
        who_sent (str): Who sent the message (usr = user, hum = lawyer, llm = model).
    """

    __tablename__ = "chats_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    content = Column(Text, nullable=False)
    content_link = Column(Text, nullable=True)
    type = Column(String(8), nullable=False)
    sent_at = Column(TIMESTAMP(timezone=False))
    who_sent = Column(String(3), nullable=False)

    chats = relationship("Chats", back_populates="chats_messages")

    __table_args__ = (
        UniqueConstraint("chat_id", "sent_at", "who_sent", name="uq_chat_message"),
    )
