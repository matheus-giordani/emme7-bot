"""Base models for user controllers."""

from pydantic import BaseModel, Field
from typing import Optional, Any


class InternalMessageModel(BaseModel):
    """Represents a message model used internally in the code. It's a general model with core information that any WhatsApp integrator has, e.g. number of the user who sent, store's WhatsApp number being used, content of the message, etc."""

    phone: str = Field(..., description="Phone number of the user sending the message.")
    store_phone: str = Field(..., description="Store's WhatsApp number.")
    last_interacted_at: str = Field(
        ..., description="Timestamp when the message was received."
    )
    content: Optional[str] = Field(..., description="Content of the message.")
    content_link: Optional[str] = Field(
        ...,
        description="Link of the content of the message (if it is an image/video/audio...).",
    )
    type: str = Field(
        ...,
        description="Type of the message (if it is an image/video/audio...).",
    )
    who_sent: str = Field(
        ...,
        description="Who sent the message.",
    )
    pending_message: Optional[str] = None
    additional_info: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional information as a dictionary with any keys.",
    )
    send_to_wpp: bool = Field(..., description="Whether to send to WhatsApp or not.")
    use_llm: bool = Field(
        ...,
        description="Whether to use LLM in the chatbot or not (if not it's a test).",
    )


class RedisModel(BaseModel):
    """Data model for the response of the redis endpoint."""

    status: str = Field(..., description="Status of the redis workflow (success).")


class ChatbotResponse(BaseModel):
    """Data model for the response of the chatbot."""

    response: str = Field(..., description="LLM's generated response.")
