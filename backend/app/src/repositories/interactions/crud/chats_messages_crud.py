"""
CRUD operations for managing chats messages in the database.

This module provides a `CRUDChatsMessages` class with methods to:
- Retrieve a single message by ID.
- Retrieve messages by chat_id.
- Create a new message.
- Delete a message by ID.
"""

from typing import Optional, List
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session
from datetime import datetime
from src.repositories.interactions.models.chats_messages_model import ChatsMessages
from src.repositories.interactions.schemas.chats_messages_schema import (
    ChatsMessagesCreate,
)


class CRUDChatsMessages:
    """
    Repository class for handling database operations related to chats messages.

    This class provides methods to interact with the database, including
    fetching, creating, and deleting messages.
    """

    def __init__(self) -> None:
        """Init class."""
        pass

    def get(self, db: Session, message_id: int) -> Optional[ChatsMessages]:
        """
        Retrieve a message by its ID.

        Args:
            db (Session): The database session.
            message_id (int): The ID of the message to retrieve.

        Returns:
            Optional[ChatsMessages]: The message object if found, otherwise None.
        """
        return db.query(ChatsMessages).filter(ChatsMessages.id == message_id).first()

    def get_by_chat_id(
        self, db: Session, chat_id: int, number_of_messages: int
    ) -> List[ChatsMessages]:
        """
        Retrieve the last 10 messages for a specific chat.

        Args:
            db (Session): The database session.
            chat_id (int): The ID of the chat to retrieve messages for.
            number_of_messages (int): Number of messages to retrieve.

        Returns:
            List[Messages]: List of the last 10 messages for the specified chat.
        """
        messages: List[ChatsMessages] = (
            db.query(ChatsMessages)
            .filter(ChatsMessages.chat_id == chat_id)
            .order_by(desc(ChatsMessages.sent_at))
            .limit(number_of_messages)
            .all()
        )
        # Reverse to get chronological order (oldest to newest)
        messages.reverse()
        return messages

    def get_last_message_by_chat_id(
        self, db: Session, chat_id: int
    ) -> Optional[ChatsMessages]:
        """
        Retrieve the last message for a specific chat.

        Args:
            db (Session): The database session.
            chat_id (int): The ID of the chat to retrieve the last message for.

        Returns:
            Optional[ChatsMessages]: The last message object if found, otherwise None.
        """
        return (
            db.query(ChatsMessages)
            .filter(ChatsMessages.chat_id == chat_id)
            .order_by(desc(ChatsMessages.sent_at))
            .first()
        )

    def get_last_message_by_chat_id_and_sender(
        self, db: Session, chat_id: int, who_sent: str
    ) -> Optional[ChatsMessages]:
        """Return the most recent message for a given chat filtered by sender."""

        return (
            db.query(ChatsMessages)
            .filter(
                ChatsMessages.chat_id == chat_id,
                ChatsMessages.who_sent == who_sent,
            )
            .order_by(desc(ChatsMessages.sent_at))
            .first()
        )

    def get_recent_media_by_chat_id(
        self, db: Session, chat_id: int, limit: int = 10
    ) -> List[ChatsMessages]:
        """Return recent non-text messages or those with attachments."""

        return (
            db.query(ChatsMessages)
            .filter(
                ChatsMessages.chat_id == chat_id,
                ChatsMessages.who_sent == "usr",
                or_(
                    ChatsMessages.type != "text",
                    ChatsMessages.content_link.isnot(None),
                ),
            )
            .order_by(desc(ChatsMessages.sent_at))
            .limit(limit)
            .all()
        )

    def create(self, db: Session, message_in: ChatsMessagesCreate) -> ChatsMessages:
        """
        Create a new message in the database.

        Args:
            db (Session): The database session.
            message_in (ChatsMessagesCreate): The message data to be inserted.

        Returns:
            ChatsMessages: The newly created message object.
        """
        db_message = ChatsMessages(**message_in.model_dump())
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        return db_message

    def delete(self, db: Session, message_id: int) -> Optional[ChatsMessages]:
        """
        Delete a message by its ID.

        Args:
            db (Session): The database session.
            message_id (int): The ID of the message to delete.

        Returns:
            Optional[ChatsMessages]: The deleted message object if found, otherwise None.
        """
        message = self.get(db, message_id)
        if message:
            db.delete(message)
            db.commit()
            return message
        return None

    def message_exists(
        self,
        db: Session,
        chat_id: int,
        sent_at: datetime,
        who_sent: str,
    ) -> bool:
        """
        Check if a message with the same unique combination already exists.

        Args:
            db (Session): The database session.
            chat_id (int): ID of the chat.
            content (str): The text content of the message.
            sent_at (datetime): When the message was received.
            who_sent (str): Who sent the message.

        Returns:
            bool: True if message exists, False otherwise.
        """
        existing_message = (
            db.query(ChatsMessages)
            .filter(
                ChatsMessages.chat_id == chat_id,
                ChatsMessages.sent_at == sent_at,
                ChatsMessages.who_sent == who_sent,
            )
            .first()
        )
        return existing_message is not None
