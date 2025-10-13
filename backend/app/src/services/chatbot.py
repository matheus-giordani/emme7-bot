"""Persist incoming messages and orchestrate the furniture store assistant."""

from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from fastapi import Depends
from sqlalchemy.orm import Session

from src.agents.graph_agents import ChatBotGraph
from src.models.user_models import InternalMessageModel
from src.repositories.interactions.models.customer_leads_model import CustomerLead
from src.services.interactions.chats_messages_services import (
    ChatMessageService,
    get_chats_messages_service,
)
from src.services.interactions.chats_services import ChatsService, get_chats_service
from src.services.interactions.customer_leads_service import (
    CustomerLeadService,
    get_customer_lead_service,
)
from src.services.messaging.whatsapp.evolution_client import EvolutionClient
from src.services.store_routing import get_store_contacts


class ChatBot:
    """Handle conversations with the sales assistant agent."""

    HUMAN_COOLDOWN = timedelta(minutes=5)

    def __init__(
        self,
        chatbot_graph: ChatBotGraph,
        chats_service: ChatsService,
        chats_messages_service: ChatMessageService,
        customer_lead_service: CustomerLeadService,
        whatsapp_client: EvolutionClient,
    ) -> None:
        self.chatbot_graph = chatbot_graph
        self.chats_service = chats_service
        self.chats_messages_service = chats_messages_service
        self.customer_lead_service = customer_lead_service
        self.whatsapp_client = whatsapp_client
        self.store_name = os.getenv("STORE_NAME", "Loja de Móveis")
        self.info_forward_number = os.getenv("STORE_INFO_FORWARD_NUMBER")
        self.responsible_number = os.getenv("STORE_RESPONSIBLE_NUMBER")

    def run(self, db: Session, data: List[InternalMessageModel]) -> str:
        """Execute the assistant flow for a batch of incoming messages."""
        if not data:
            raise ValueError("Nenhuma mensagem recebida para processamento.")

        last_message = data[-1]
        chat_id = self.chats_service.upsert(
            db,
            last_message.phone,
            last_message.store_phone,
            self._as_datetime(last_message.last_interacted_at),
        )
        if not isinstance(chat_id, int):  # defensive guard
            raise ValueError("chat_id must have um valor inteiro.")

        for message in data:
            sent_at = self._as_datetime(message.last_interacted_at)

            if not self._should_store_message(db, chat_id, message, sent_at):
                continue

            created = self.chats_messages_service.create(
                db,
                chat_id=chat_id,
                content=message.content or "",
                content_link=message.content_link,
                _type=message.type,
                sent_at=sent_at,
                who_sent=message.who_sent,
            )
            if created is None:
                continue

        last_message_dt = self._as_datetime(last_message.last_interacted_at)

        if not last_message.use_llm:
            return "Mensagem de teste. Opção por não usar LLM."

        if self._is_human_cooldown_active(db, chat_id, last_message_dt, last_message.who_sent):
            return "Atendimento humano em andamento. A LLM ficará pausada por 5 minutos após a última resposta humana."

        chat_messages = self.chats_messages_service.get_by_chat_id(db, chat_id, 10)
        existing_lead = self.customer_lead_service.by_phone(db, last_message.phone)
        context = self._build_context(last_message, existing_lead)
        llm_message = self.chatbot_graph.run(data, chat_messages, context)

        if last_message.send_to_wpp:
            self.whatsapp_client.send_message(
                phone=last_message.phone,
                message=llm_message,
            )

        try:
            self.chats_messages_service.create(
                db,
                chat_id=chat_id,
                content=llm_message,
                content_link=None,
                _type="text",
                sent_at=datetime.now(timezone.utc),
                who_sent="llm",
            )
        except Exception as exc:  # pragma: no cover - defensive log path
            print(f"Não foi possível registrar a resposta do LLM: {exc}")

        return llm_message

    def _build_context(
        self, last_message: InternalMessageModel, lead: CustomerLead | None
    ) -> Dict[str, Dict[str, Any]]:
        """Assemble store/customer context to guide the agent."""
        context: Dict[str, Dict[str, Any]] = {
            "store": {
                "name": self.store_name,
                "entry_phone": last_message.store_phone,
            },
            "customer": {
                "phone": last_message.phone,
            },
        }
        if self.info_forward_number:
            context["store"]["info_forward_number"] = self.info_forward_number
        if self.responsible_number:
            context["store"]["responsible_number"] = self.responsible_number
        contacts = [contact.as_dict() for contact in get_store_contacts()]
        if contacts:
            context["store"]["routing_contacts"] = contacts
        if lead:
            context["lead"] = {
                "id": lead.id,
                "name": lead.name,
                "phone": lead.phone,
                "email": lead.email,
                "city": lead.city,
                "product_interest": lead.product_interest,
                "notes": lead.notes,
            }
            context["customer"]["name"] = lead.name
        return context

    def _as_datetime(self, value: Any) -> datetime:
        """Best-effort conversion of timestamps coming from webhook payloads."""
        if isinstance(value, datetime):
            return self._ensure_timezone(value)
        if isinstance(value, str):
            cleaned = value.replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(cleaned)
                return self._ensure_timezone(parsed)
            except ValueError:
                pass
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc)
            except (ValueError, TypeError):
                pass
        return datetime.now(timezone.utc)

    def _ensure_timezone(self, value: datetime) -> datetime:
        """Normalize datetime objects to timezone-aware UTC instances."""

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _should_store_message(
        self,
        db: Session,
        chat_id: int,
        message: InternalMessageModel,
        sent_at: datetime,
    ) -> bool:
        """Decide whether the incoming message should be persisted."""

        if message.who_sent != "hum":
            return True

        last_llm = self.chats_messages_service.get_last_message_from_sender(
            db, chat_id, "llm"
        )
        if not last_llm or not last_llm.sent_at:
            return True

        last_llm_dt = self._ensure_timezone(last_llm.sent_at)
        # Drop duplicates caused by the LLM echoing through Evolution webhook.
        if (
            abs((sent_at - last_llm_dt).total_seconds()) <= 20
            and (last_llm.content or "").strip() == (message.content or "").strip()
        ):
            return False

        return True

    def _is_human_cooldown_active(
        self,
        db: Session,
        chat_id: int,
        reference_time: datetime,
        last_sender: str,
    ) -> bool:
        """Return True when a human responded in the last HUMAN_COOLDOWN window."""

        if last_sender == "hum":
            return True

        last_human = self.chats_messages_service.get_last_message_from_sender(
            db, chat_id, "hum"
        )
        if not last_human or not last_human.sent_at:
            return False

        last_human_dt = self._ensure_timezone(last_human.sent_at)
        if reference_time < last_human_dt:
            reference_time = last_human_dt

        return reference_time - last_human_dt <= self.HUMAN_COOLDOWN


def get_chatbot(
    chatbot_graph: ChatBotGraph = Depends(),
    chats_service: ChatsService = Depends(get_chats_service),
    chats_messages_service: ChatMessageService = Depends(get_chats_messages_service),
    customer_lead_service: CustomerLeadService = Depends(get_customer_lead_service),
) -> ChatBot:
    """FastAPI dependency that wires the chatbot with Evolution API credentials."""
    evolution_api_url = os.getenv("EVOLUTION_API_URL")
    evolution_api_key = os.getenv("EVOLUTION_API_KEY")
    evolution_instance_name = os.getenv("EVOLUTION_INSTANCE_NAME")

    assert (
        evolution_api_url and evolution_api_key and evolution_instance_name
    ), "Variáveis EVOLUTION_API_URL, EVOLUTION_API_KEY e EVOLUTION_INSTANCE_NAME devem estar configuradas no ambiente."

    evolution_client = EvolutionClient(
        base_url=evolution_api_url,
        api_key=evolution_api_key,
        instance_name=evolution_instance_name,
    )
    return ChatBot(
        chatbot_graph,
        chats_service,
        chats_messages_service,
        customer_lead_service,
        evolution_client,
    )
