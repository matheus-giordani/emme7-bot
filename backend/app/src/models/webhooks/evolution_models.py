"""Pydantic models describing Evolution API webhook payloads."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class WebhookEvent(str, Enum):
    """Subset of events emitted by the Evolution API that we care about."""

    MESSAGES_UPSERT = "messages.upsert"
    MESSAGES_UPDATE = "messages.update"
    MESSAGES_DELETE = "messages.delete"
    CHATS_UPDATE = "chats.update"
    CONNECTION_UPDATE = "connection.update"
    APPLICATION_STARTUP = "application.startup"


class MessageKey(BaseModel):
    """Primary identifier for a WhatsApp message."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    remote_jid: str = Field(alias="remoteJid")
    from_me: bool = Field(alias="fromMe")
    id: str
    participant: Optional[str] = None


class ExtendedTextMessage(BaseModel):
    """Extended text payload with Evolution-specific metadata."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    text: Optional[str] = None
    preview_type: Optional[str] = Field(default=None, alias="previewType")
    canonical_url: Optional[str] = Field(default=None, alias="canonicalUrl")
    matched_text: Optional[str] = Field(default=None, alias="matchedText")
    description: Optional[str] = None
    title: Optional[str] = None


class MediaMessage(BaseModel):
    """Common attributes for media payloads."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    caption: Optional[str] = None
    mimetype: Optional[str] = Field(default=None, alias="mimetype")
    file_length: Optional[int] = Field(default=None, alias="fileLength")
    file_sha256: Optional[str] = Field(default=None, alias="fileSha256")
    media_key: Optional[str] = Field(default=None, alias="mediaKey")
    direct_path: Optional[str] = Field(default=None, alias="directPath")
    url: Optional[str] = None


class ImageMessage(MediaMessage):
    height: Optional[int] = None
    width: Optional[int] = None


class VideoMessage(MediaMessage):
    seconds: Optional[int] = None
    gif_playback: Optional[bool] = Field(default=None, alias="gifPlayback")


class AudioMessage(MediaMessage):
    seconds: Optional[int] = None
    ptt: Optional[bool] = None


class DocumentMessage(MediaMessage):
    file_name: Optional[str] = Field(default=None, alias="fileName")


class StickerMessage(MediaMessage):
    is_animated: Optional[bool] = Field(default=None, alias="isAnimated")


class ReactionMessage(BaseModel):
    """Emoji reaction linked to another message."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    key: Optional[MessageKey] = None
    text: Optional[str] = None
    sender_timestamp_ms: Optional[int] = Field(default=None, alias="senderTimestampMs")


class MessageContent(BaseModel):
    """Union of WhatsApp message body variants."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    conversation: Optional[str] = None
    extended_text_message: Optional[ExtendedTextMessage] = Field(
        default=None, alias="extendedTextMessage"
    )
    image_message: Optional[ImageMessage] = Field(default=None, alias="imageMessage")
    video_message: Optional[VideoMessage] = Field(default=None, alias="videoMessage")
    audio_message: Optional[AudioMessage] = Field(default=None, alias="audioMessage")
    document_message: Optional[DocumentMessage] = Field(
        default=None, alias="documentMessage"
    )
    sticker_message: Optional[StickerMessage] = Field(
        default=None, alias="stickerMessage"
    )
    reaction_message: Optional[ReactionMessage] = Field(
        default=None, alias="reactionMessage"
    )
    ephemeral_message: Optional["EphemeralMessage"] = Field(
        default=None, alias="ephemeralMessage"
    )
    view_once_message_v2: Optional["ViewOnceMessageV2"] = Field(
        default=None, alias="viewOnceMessageV2"
    )


class EphemeralMessage(BaseModel):
    """Wrapper for disappearing messages."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    message: Optional[MessageContent] = None
    message_timestamp: Optional[int] = Field(default=None, alias="messageTimestamp")


class ViewOnceMessageV2(BaseModel):
    """Wrapper for view-once media."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    message: Optional[MessageContent] = None


MessageContent.model_rebuild()


class WhatsAppMessage(BaseModel):
    """Typed WhatsApp message with useful metadata."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    key: MessageKey
    message: Optional[MessageContent] = None
    message_type: Optional[str] = Field(default=None, alias="messageType")
    message_timestamp: Optional[int] = Field(default=None, alias="messageTimestamp")
    push_name: Optional[str] = Field(default=None, alias="pushName")
    broadcast: Optional[bool] = None
    status: Optional[str] = None
    media_type: Optional[str] = Field(default=None, alias="mediaType")
    from_: Optional[str] = Field(default=None, alias="from")
    sender: Optional[str] = Field(default=None, alias="sender")
    participant: Optional[str] = None


class MessageUpsertType(str, Enum):
    """Types of upsert events delivered by Evolution."""

    NOTIFY = "notify"
    APPEND = "append"
    REPLACE = "replace"


class MessageUpsertData(BaseModel):
    """Envelope describing a batch of messages."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    type: MessageUpsertType
    messages: List[WhatsAppMessage] = Field(default_factory=list)
    last_message_number: Optional[int] = Field(default=None, alias="lastMessageNumber")
    is_historical: Optional[bool] = Field(default=None, alias="isHistorical")


class WebhookEnvelope(BaseModel):
    """Base metadata shared by all webhook events."""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True, extra="allow")

    event: str
    session: Optional[str] = None
    instance_id: Optional[str] = Field(default=None, alias="instanceId")
    timestamp: Optional[int] = None
    message_number: Optional[int] = Field(default=None, alias="messageNumber")


class MessageUpsertEnvelope(WebhookEnvelope):
    event: Literal[WebhookEvent.MESSAGES_UPSERT.value]
    data: MessageUpsertData


class GenericEnvelope(WebhookEnvelope):
    data: Any = None


WebhookPayload = WebhookEnvelope


def iter_incoming_messages(payload: WebhookPayload) -> Sequence[WhatsAppMessage]:
    """Return the messages contained in the payload, if any."""

    if payload.event == WebhookEvent.MESSAGES_UPSERT.value:
        try:
            envelope = MessageUpsertEnvelope.model_validate(payload.model_dump())
            return envelope.data.messages
        except ValidationError:
            data_obj = getattr(payload, "data", None)
            if isinstance(data_obj, dict):
                raw_messages = data_obj.get("messages")
                if isinstance(raw_messages, list):
                    typed_messages: List[WhatsAppMessage] = []
                    for item in raw_messages:
                        if isinstance(item, dict):
                            try:
                                typed_messages.append(WhatsAppMessage.model_validate(item))
                            except ValidationError:
                                continue
                    if typed_messages:
                        return typed_messages

                try:
                    return [WhatsAppMessage.model_validate(data_obj)]
                except ValidationError:
                    pass

    if isinstance(payload.data, dict):
        raw_messages = payload.data.get("messages")
        if isinstance(raw_messages, list):
            typed_messages: List[WhatsAppMessage] = []
            for item in raw_messages:
                if isinstance(item, dict):
                    try:
                        typed_messages.append(WhatsAppMessage.model_validate(item))
                    except ValidationError:
                        continue
            if typed_messages:
                return typed_messages

        if all(key in payload.data for key in ("key", "message")):
            try:
                return [WhatsAppMessage.model_validate(payload.data)]
            except ValidationError:
                pass

    return []


def walk_message_wrappers(message: Optional[MessageContent]) -> Optional[MessageContent]:
    """Unwrap Evolution containers (ephemeral/view-once) to reach the real payload."""

    current = message
    visited: set[int] = set()
    while current is not None:
        current_id = id(current)
        if current_id in visited:
            break
        visited.add(current_id)

        if current.ephemeral_message and current.ephemeral_message.message:
            current = current.ephemeral_message.message
            continue

        if current.view_once_message_v2 and current.view_once_message_v2.message:
            current = current.view_once_message_v2.message
            continue

        return current

    return current


def yield_incoming_user_messages(payload: WebhookPayload) -> Iterable[WhatsAppMessage]:
    """Iterate only over messages that were sent by the remote user."""

    for message in iter_incoming_messages(payload):
        if message.key.from_me:
            continue
        yield message
