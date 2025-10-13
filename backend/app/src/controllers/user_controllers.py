"""Receive and process messages from the client.

Handle incoming messages, process them, and store relevant
data in the database.
"""
from typing import List
from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.orm import Session
from src.repositories.interactions.dependencies import get_db
from src.models.user_models import (
    InternalMessageModel,
    ChatbotResponse,
)

from src.services.chatbot import ChatBot, get_chatbot

user_router = APIRouter(prefix="/user", tags=["Users"])


@user_router.post(
    "/process_message",
    responses={
        200: {"model": ChatbotResponse, "description": "Successful Response"},
    },
)
def process_message(
    data: List[InternalMessageModel],
    db: Session = Depends(get_db),
    chatbot: ChatBot = Depends(get_chatbot),
) -> ChatbotResponse:
    """
    Receives a list of InternalMessageModel.

    Args:
        data (List[InternalMessageModel]): List of the incoming
        webhook data encapsulated in a Pydantic model.

    Returns:
        ChatbotResponse if the operation is successful.
    """
    try:
        llm_message = chatbot.run(db, data)

        return ChatbotResponse(response=llm_message)
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
