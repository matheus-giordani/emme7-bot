"""This module defines the Chats model for storing chats in the database."""

from sqlalchemy import Column, String, TIMESTAMP, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.repositories.interactions.database import Base


class Chats(Base):  # type: ignore
    """Represents a chat entity in the database for the furniture store."""

    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(15), nullable=False)
    store_phone = Column(String(15), nullable=False)
    created_at = Column(TIMESTAMP(timezone=False), server_default=func.now())
    last_interacted_at = Column(TIMESTAMP(timezone=False), nullable=True)

    __table_args__ = (
        UniqueConstraint("phone", "store_phone", name="uq_phone_combination"),
    )

    chats_messages = relationship(
        "ChatsMessages", back_populates="chats", cascade="all, delete"
    )
