"""
This module defines Pydantic models for handling chat-related data.

It includes base validation for chat attributes, as well as models for
creating and responding to chat data.
"""

from pydantic import BaseModel, StringConstraints
from typing import Annotated
from datetime import datetime


class ChatBase(BaseModel):
    """
    Represents the base structure for a chat.

    Attributes:
        phone (str): Phone number of the customer in the chat.
        store_phone (str): Phone number of the store instance talking to the user.
        last_interacted_at (timestamp): The last time that the chat has received a message.

    """

    phone: Annotated[str, StringConstraints(max_length=15)]
    store_phone: str
    last_interacted_at: datetime


class ChatCreate(ChatBase):
    """
    Represents the data required to create a new chat.

    Inherits all fields from ChatBase.
    """

    pass
