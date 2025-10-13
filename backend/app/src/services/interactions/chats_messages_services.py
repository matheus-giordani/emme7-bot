"""This module provides the ChatMessageService class for managing messages in the application."""

from sqlalchemy.orm import Session
from typing import Optional, List
from fastapi import Depends
from datetime import datetime
from src.repositories.interactions.crud.chats_messages_crud import CRUDChatsMessages
from src.repositories.interactions.models.chats_messages_model import ChatsMessages
from src.repositories.interactions.schemas.chats_messages_schema import (
    ChatsMessagesCreate,
)


class ChatMessageService:
    """Service layer for handling message-related operations."""

    def __init__(self, chat_message_repository: CRUDChatsMessages):
        """
        Initialize the ChatMessageService with a CRUD repository.

        Args:
            chat_message_repository (CRUDMessage): Dependency-injected repository
            for message-related database operations.
        """
        self.chat_message_repository = chat_message_repository

    def get(self, db: Session, message_id: int) -> Optional[ChatsMessages]:
        """
        Retrieve a message by its ID.

        Args:
            db (Session): The database session.
            message_id (int): The ID of the message to retrieve.

        Returns:
            Optional[ChatsMessages]: The message object if found, otherwise None.
        """
        return self.chat_message_repository.get(db, message_id)

    def get_by_chat_id(
        self, db: Session, chat_id: int, number_of_messages: int
    ) -> List[ChatsMessages]:
        """
        Retrieve all messages for a specific chat.

        Args:
            db (Session): The database session.
            chat_id (int): The ID of the chat to retrieve messages for.
            number_of_messages (int): Number of messages to retrieve.

        Returns:
            List[ChatsMessages]: List of messages for the specified chat.
        """
        messages: List[ChatsMessages] = self.chat_message_repository.get_by_chat_id(
            db, chat_id, number_of_messages
        )
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
        return self.chat_message_repository.get_last_message_by_chat_id(db, chat_id)

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
            sent_at (datetime): When the message was received.
            who_sent (str): Who sent the message.

        Returns:
            bool: True if message exists, False otherwise.
        """
        message_exists: bool = self.chat_message_repository.message_exists(
            db, chat_id, sent_at, who_sent
        )
        return message_exists

    def get_last_message_from_sender(
        self, db: Session, chat_id: int, who_sent: str
    ) -> Optional[ChatsMessages]:
        """Return the most recent message in a chat authored by the provided sender code."""

        return self.chat_message_repository.get_last_message_by_chat_id_and_sender(
            db, chat_id, who_sent
        )

    def create(
        self,
        db: Session,
        chat_id: int,
        content: str,
        content_link: Optional[str],
        _type: str,
        sent_at: datetime,
        who_sent: str,
    ) -> Optional[ChatsMessages]:
        """
        Create a new message if it doesn't already exist.

        Args:
            db (Session): The database session.
            chat_id (int): ID of the chat.
            content (str): The text content of the message.
            content_link (Optional[str]): Link associated with the message.
            _type (str): The type of the message.
            sent_at (datetime): When the message was received.
            who_sent (str): Who sent the message.

        Returns:
            Optional[ChatsMessages]: The created message object if created, None if already exists.
        """
        # Check if message already exists (using simplified constraint)
        if self.message_exists(db, chat_id, sent_at, who_sent):
            return None

        message_in = ChatsMessagesCreate(
            chat_id=chat_id,
            content=content,
            content_link=content_link,
            type=_type,
            sent_at=sent_at,
            who_sent=who_sent,
        )
        return self.chat_message_repository.create(db, message_in)

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
        if not message:
            raise ValueError("Message not found")
        return self.chat_message_repository.delete(db, message_id)


# Dependency Injection for FastAPI
def get_chats_messages_service(
    chat_message_repository: CRUDChatsMessages = Depends(),
) -> ChatMessageService:
    """Retrieve an instance of ChatMessageService with the provided repository."""
    return ChatMessageService(chat_message_repository)
