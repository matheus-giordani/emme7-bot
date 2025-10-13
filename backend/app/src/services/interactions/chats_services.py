"""This module provides the ChatsService class for managing chats in the application."""

from sqlalchemy.orm import Session
from typing import Optional
from fastapi import Depends
from datetime import datetime

from src.repositories.interactions.crud.chats_crud import CRUDChat
from src.repositories.interactions.models.chats_model import Chats


class ChatsService:
    """Service layer for handling chat-related operations."""

    def __init__(self, chat_repository: CRUDChat):
        """
        Initialize the ChatsService with a CRUD repository.

        Args:
            chat_repository (CRUDChat): Repository for chat-related database operations.
        """
        self.chat_repository = chat_repository

    def get_id(self, db: Session, phone: str, store_phone: str) -> Optional[Chats]:
        """
        Retrieve a chat ID by phone number and store_phone.

        Args:
            db (Session): The database session.
            phone (str): The phone number of the user in the chat.
            store_phone (str): Phone number of the store instance talking to the user.

        Returns:
            Optional[Chats]: The chat object if found, otherwise None.
        """
        chats = self.chat_repository.get(db, phone, store_phone)
        return chats.id

    def get(self, db: Session, phone: str, store_phone: str) -> Optional[Chats]:
        """
        Retrieve a chat by phone number and store_phone.

        Args:
            db (Session): The database session.
            phone (str): The phone number of the user in the chat.
            store_phone (str): Phone number of the store instance talking to the user.

        Returns:
            Optional[Chats]: The chat object if found, otherwise None.
        """
        return self.chat_repository.get(db, phone, store_phone)

    def delete(self, db: Session, phone: str, store_phone: str) -> Optional[Chats]:
        """
        Delete a chat by phone number and store_phone.

        Args:
            db (Session): The database session.
            phone (str): The phone number of the user in the chat.
            store_phone (str): Phone number of the store instance talking to the user.

        Returns:
            Optional[Chats]: The deleted chat object if found, otherwise None.
        """
        chat = self.get(db, phone, store_phone)
        if not chat:
            raise ValueError("Chat not found")
        return self.chat_repository.delete(db, phone, store_phone)

    def upsert(
        self,
        db: Session,
        phone: str,
        store_phone: str,
        last_interacted_at: datetime,
    ) -> int:
        """
        Create or update a chat based on phone and store_phone. If the chat exists, only update the last_interacted_at field.

        Args:
            db (Session): The database session.
            phone (str): Phone number of the user in the chat.
            store_phone (str): Phone number of the store instance talking to the user.
            last_interacted_at (datetime): The last time that the chat has received a message.

        Returns:
            Chats: The created or updated chat object.
        """
        chat = self.chat_repository.upsert(
            db,
            phone,
            store_phone,
            last_interacted_at,
        )
        chat_id: int = chat.id
        return chat_id


# Dependency for FastAPI
def get_chats_service(chat_repository: CRUDChat = Depends()) -> ChatsService:
    """Retrieve an instance of ChatsService with the provided repository."""
    return ChatsService(chat_repository)
