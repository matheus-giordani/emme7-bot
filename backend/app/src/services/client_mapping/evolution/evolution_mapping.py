"""Map Evolution API webhook payloads into the internal message model."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.models.user_models import InternalMessageModel
from src.models.webhooks.evolution_models import (
    WhatsAppMessage,
    WebhookPayload,
    iter_incoming_messages,
    walk_message_wrappers,
)
from src.services.process_audio import ProcessAudio


class EvolutionStorePhoneResolver:
    """Resolve which store WhatsApp instance handled a webhook message."""

    def __init__(
        self,
        default_phone: Optional[str],
        session_phone_map: Dict[str, str],
    ) -> None:
        self.default_phone = default_phone
        self.session_phone_map = session_phone_map

    def __call__(self, payload: WebhookPayload) -> str:
        session = getattr(payload, "session", None)
        if session and session in self.session_phone_map:
            return self.session_phone_map[session]

        if self.default_phone:
            return self.default_phone

        if session and session.isdigit():
            return session

        raise ValueError(
            "Não foi possível determinar o número da loja responsável pelo atendimento."
        )


def _parse_session_phone_map(raw_value: Optional[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not raw_value:
        return mapping

    pairs = [entry.strip() for entry in raw_value.split(",") if entry.strip()]
    for pair in pairs:
        if "=" in pair:
            session, phone = pair.split("=", 1)
        elif ":" in pair:
            session, phone = pair.split(":", 1)
        else:
            continue

        normalized_phone = _normalize_phone(phone)
        if not normalized_phone:
            continue

        mapping[session.strip()] = normalized_phone

    return mapping


def _normalize_phone(value: str) -> Optional[str]:
    digits = re.sub(r"\D", "", value or "")
    return digits or None


def _jid_to_phone(jid: str) -> Optional[str]:
    if not jid:
        return None

    if jid.endswith("@g.us"):
        # Ignore group conversations for now.
        return None

    local_part = jid.split("@", 1)[0]
    return _normalize_phone(local_part)


class EvolutionMapping:
    """Translate Evolution webhook events into InternalMessageModel instances."""

    def __init__(
        self,
        process_audio: ProcessAudio,
        store_phone_resolver: EvolutionStorePhoneResolver,
        default_send_to_wpp: bool = True,
        default_use_llm: bool = True,
    ) -> None:
        self.process_audio = process_audio
        self.store_phone_resolver = store_phone_resolver
        self.default_send_to_wpp = default_send_to_wpp
        self.default_use_llm = default_use_llm

    def map_payload_to_internal_messages(
        self,
        payload: WebhookPayload,
        who_sent: str,
        pending_message: str,
    ) -> List[InternalMessageModel]:
        store_phone = self.store_phone_resolver(payload)

        messages: List[InternalMessageModel] = []
        for message in iter_incoming_messages(payload):
            from_me = bool(message.key.from_me)
            actual_who_sent = "hum" if from_me else who_sent

            # When the message was sent by the store (human operator), do not
            # trigger the LLM nor enqueue another WhatsApp send.
            send_to_wpp = False if from_me else self.default_send_to_wpp
            use_llm = False if from_me else self.default_use_llm

            # Pending message indicates which actor is expected to reply next.
            # For user-originated messages we keep the original behaviour.
            actual_pending = pending_message if not from_me else who_sent

            mapped = self._map_single_message(
                payload=payload,
                message=message,
                store_phone=store_phone,
                who_sent=actual_who_sent,
                pending_message=actual_pending,
                send_to_wpp=send_to_wpp,
                use_llm=use_llm,
            )
            if mapped is not None:
                messages.append(mapped)

        return messages

    def _map_single_message(
        self,
        payload: WebhookPayload,
        message: WhatsAppMessage,
        store_phone: str,
        who_sent: str,
        pending_message: str,
        send_to_wpp: bool,
        use_llm: bool,
    ) -> Optional[InternalMessageModel]:
        user_phone = _jid_to_phone(message.key.remote_jid)
        if not user_phone or user_phone == store_phone:
            candidates = [
                getattr(message, "from_", None),
                message.sender,
                message.participant,
            ]
            data_obj = getattr(payload, "data", None)
            if isinstance(data_obj, dict):
                candidates.extend(
                    [
                        data_obj.get("sender"),
                        data_obj.get("from"),
                    ]
                )

            for candidate in candidates:
                user_phone = _jid_to_phone(candidate) or user_phone
                if user_phone and user_phone != store_phone:
                    break

        if not user_phone or user_phone == store_phone:
            return None

        last_interacted_at = self._unix_to_timestamp_str(
            message.message_timestamp or getattr(payload, "timestamp", None)
        )

        content, link, message_type, additional_info = self._extract_message_content(
            payload=payload, message=message
        )

        return InternalMessageModel(
            phone=user_phone,
            store_phone=store_phone,
            last_interacted_at=last_interacted_at,
            content=content,
            content_link=link,
            type=message_type,
            who_sent=who_sent,
            pending_message=pending_message,
            additional_info=additional_info,
            send_to_wpp=send_to_wpp,
            use_llm=use_llm,
        )

    def _extract_message_content(
        self,
        payload: WebhookPayload,
        message: WhatsAppMessage,
    ) -> tuple[Optional[str], Optional[str], str, Dict[str, str]]:
        body = walk_message_wrappers(message.message)

        additional: Dict[str, str] = {}
        if message.key.id:
            additional["message_id"] = message.key.id

        session = getattr(payload, "session", None)
        if session:
            additional["session"] = session

        instance_id = getattr(payload, "instance_id", None)
        if instance_id:
            additional["instance_id"] = instance_id

        if body is None:
            return None, None, "unknown", additional

        if body.reaction_message and body.reaction_message.text:
            additional["reaction"] = body.reaction_message.text
            return None, None, "reaction", additional

        if body.extended_text_message and body.extended_text_message.text:
            return (
                body.extended_text_message.text,
                None,
                "text",
                additional,
            )

        if body.conversation:
            return body.conversation, None, "text", additional

        if body.audio_message:
            link = body.audio_message.url or body.audio_message.direct_path
            transcript = self._transcribe_audio(link)
            return transcript, link, "audio", additional

        if body.image_message:
            caption = body.image_message.caption
            link = body.image_message.url or body.image_message.direct_path
            return caption, link, "image", additional

        if body.video_message:
            caption = body.video_message.caption
            link = body.video_message.url or body.video_message.direct_path
            return caption, link, "video", additional

        if body.document_message:
            link = body.document_message.url or body.document_message.direct_path
            caption = body.document_message.caption or body.document_message.file_name
            return caption, link, "document", additional

        if body.sticker_message:
            link = body.sticker_message.url or body.sticker_message.direct_path
            caption = body.sticker_message.caption if hasattr(body.sticker_message, "caption") else None
            return caption, link, "sticker", additional

        return None, None, message.message_type or "unknown", additional

    def _transcribe_audio(self, link: Optional[str]) -> str:
        if not link:
            return "Mensagem de áudio."

        try:
            transcription = self.process_audio.audio_transcription(link)
            return transcription or "Mensagem de áudio."
        except Exception:
            return "Mensagem de áudio."

    def _unix_to_timestamp_str(
        self, unix_time: Optional[int | float], fmt: str = "%Y-%m-%d %H:%M:%S.%f"
    ) -> str:
        if not unix_time:
            return datetime.now(timezone.utc).strftime(fmt)[:-3]

        ts = float(unix_time)
        if ts > 1e12:  # likely in microseconds
            ts /= 1000.0

        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.strftime(fmt)[:-3]


def get_evolution_mapping() -> EvolutionMapping:
    """FastAPI dependency to provide an EvolutionMapping instance."""

    process_audio = ProcessAudio(openai_key=os.getenv("OPENAI_API_KEY", ""))
    default_phone = _normalize_phone(os.getenv("EVOLUTION_DEFAULT_STORE_PHONE", ""))
    session_map = _parse_session_phone_map(os.getenv("EVOLUTION_SESSION_PHONE_MAP"))

    resolver = EvolutionStorePhoneResolver(
        default_phone=default_phone, session_phone_map=session_map
    )
    return EvolutionMapping(
        process_audio=process_audio, store_phone_resolver=resolver
    )
