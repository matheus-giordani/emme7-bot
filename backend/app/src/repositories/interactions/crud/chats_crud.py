"""
CRUD operations for managing chats in the database.

This module provides a `CRUDChat` class with methods to:
- Retrieve a chat by phone and store_phone.
- Delete a chat by phone and store_phone.
- Create or update a chat (upsert) based on phone and store_phone.
"""

from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
from src.repositories.interactions.models.chats_model import Chats
from src.repositories.interactions.schemas.chats_schema import ChatCreate


class CRUDChat:
    """
    Repository class for handling database operations related to chats.

    This class provides methods to interact with the database, including
    fetching, creating, updating, and deleting chats.
    """

    def __init__(self) -> None:
        """Init class."""
        pass

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
        return (
            db.query(Chats)
            .filter(Chats.phone == phone, Chats.store_phone == store_phone)
            .first()
        )

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
        if chat:
            db.delete(chat)
            db.commit()
            return chat
        return None

    def upsert(
        self,
        db: Session,
        phone: str,
        store_phone: str,
        last_interacted_at: datetime,
    ) -> Chats:
        """Insert a new chat if it doesn't exist, or update only the `last_interacted_at` field if it does exist.

        Args:
            db (Session): The database session.
            phone (str): Phone number of the user in the chat.
            store_phone (str): Phone number of the store instance talking to the user.
            last_interacted_at (datetime): The last time that the chat has received a message.

        Returns:
            Chats: The created or updated chat object.
        """
        chat = self.get(db, phone, store_phone)
        if chat:
            # Update only the last_interacted_at field
            chat.last_interacted_at = last_interacted_at
        else:
            # Create new chat
            chat = Chats(
                phone=phone,
                store_phone=store_phone,
                last_interacted_at=last_interacted_at,
            )
            db.add(chat)

        db.commit()
        db.refresh(chat)
        return chat

    def create(self, db: Session, chat_in: ChatCreate) -> Chats:
        """
        Create a new chat in the database.

        Args:
            db (Session): The database session.
            chat_in (ChatCreate): The chat data to be inserted.

        Returns:
            Chats: The newly created chat object.
        """
        db_chat = Chats(**chat_in.model_dump())
        db.add(db_chat)
        db.commit()
        db.refresh(db_chat)
        return db_chat
