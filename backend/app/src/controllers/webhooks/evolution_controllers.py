"""FastAPI endpoints for Evolution API webhooks."""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header

from src.models.user_models import RedisModel
from src.models.webhooks.evolution_models import WebhookEvent, WebhookPayload
from src.services.client_mapping.evolution.evolution_mapping import (
    EvolutionMapping,
    get_evolution_mapping,
)
from src.services.redis.redis_services import RedisService, create_redis_service


logger = logging.getLogger("evolution.webhook")

redis_host = os.getenv("REDIS_HOST")
redis_pw = os.getenv("REDIS_PASSWORD")
redis_ssl = os.getenv("REDIS_SSL")


evolution_router = APIRouter(prefix="/evolution", tags=["evolution"])


@evolution_router.post("/webhook")
async def receive_evolution_webhook(
    payload: WebhookPayload,
    x_evolution_event: Optional[str] = Header(default=None, alias="x-evolution-event"),
    evolution_mapping: EvolutionMapping = Depends(get_evolution_mapping),
    redis_service: RedisService = Depends(
        lambda: create_redis_service(
            host=redis_host,
            port=6379,
            password=redis_pw,
            ssl=redis_ssl,
        )
    ),
) -> RedisModel:
    """Recebe eventos do Evolution API e salva mensagens no Redis."""

    event_name = x_evolution_event or getattr(payload, "event", "<unknown>")

    logger.info("Evolution payload bruto: %s", payload.model_dump(mode="json"))

    if event_name != WebhookEvent.MESSAGES_UPSERT.value:
        logger.info("Ignorando evento Evolution '%s'", event_name)
        return RedisModel(status="ignored")

    messages = evolution_mapping.map_payload_to_internal_messages(
        payload, who_sent="usr", pending_message="llm"
    )

    if not messages:
        logger.info("Evento Evolution '%s' sem mensagens processáveis", event_name)
        return RedisModel(status="ignored")

    for internal_message in messages:
        redis_service.save(internal_message)
        logger.debug(
            "Mensagem salva no Redis: phone=%s store_phone=%s",
            internal_message.phone,
            internal_message.store_phone,
        )

    logger.info(
        "Processadas %d mensagem(ns) do evento Evolution '%s' (session=%s)",
        len(messages),
        event_name,
        getattr(payload, "session", None),
    )

    return RedisModel(status="success")
