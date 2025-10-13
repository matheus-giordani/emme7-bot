"""
This module defines Pydantic models for handling message-related data.

It includes base validation for message attributes, as well as models for creating and responding to messages.
"""

from pydantic import BaseModel, StringConstraints
from typing import Annotated, Optional
from datetime import datetime


class ChatsMessagesBase(BaseModel):
    """
    Represents the base structure for a message.

    Attributes:
        chat_id (int): ID of the chat.
        content (str): The message content.
        content_link (str): Link associated with the message (if it is an audio, image, video...)
        type (str): The type of message, with a maximum length of 5 characters.
        who_sent (str): Indicates who sent the message, with a maximum length of 3 characters.
        pending_message (str): A flag indicating if the message is pending, with a maximum length of 3 characters.
    """

    chat_id: int
    content: str
    content_link: Optional[str]
    type: Annotated[str, StringConstraints(max_length=8)]
    sent_at: datetime
    who_sent: Annotated[str, StringConstraints(max_length=3)]


class ChatsMessagesCreate(ChatsMessagesBase):
    """
    Represents the data required to create a new message.

    Inherits all fields from MessageBase.
    """

    pass
