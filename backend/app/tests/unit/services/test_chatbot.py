from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
import os
import sys
import types

import pytest


fastapi_stub = types.ModuleType("fastapi")
fastapi_stub.Depends = lambda *args, **kwargs: None
sys.modules.setdefault("fastapi", fastapi_stub)

openai_stub = types.ModuleType("openai")
openai_stub.OpenAI = MagicMock
openai_stub.NOT_GIVEN = object()
openai_types_module = types.ModuleType("openai.types")
openai_types_chat_module = types.ModuleType("openai.types.chat")
openai_types_chat_module.ChatCompletionToolParam = object
openai_types_chat_module.ChatCompletionNamedToolChoiceParam = object
openai_types_module.chat = openai_types_chat_module
openai_stub.types = SimpleNamespace(chat=openai_types_chat_module)
sys.modules.setdefault("openai", openai_stub)
sys.modules.setdefault("openai.types", openai_types_module)
sys.modules.setdefault("openai.types.chat", openai_types_chat_module)

graph_agents_stub = types.ModuleType("src.agents.graph_agents")


class _FakeGraph:
    def run(self, *_args, **_kwargs):
        return ""


graph_agents_stub.ChatBotGraph = _FakeGraph
sys.modules.setdefault("src.agents.graph_agents", graph_agents_stub)

database_stub = types.ModuleType("src.repositories.interactions.database")
database_stub.Base = object()
database_stub.SessionLocal = MagicMock
database_stub.engine = MagicMock()
sys.modules.setdefault("src.repositories.interactions.database", database_stub)

models_package = types.ModuleType("src.repositories.interactions.models")
models_package.__path__ = []  # type: ignore[attr-defined]
sys.modules.setdefault("src.repositories.interactions.models", models_package)

customer_leads_model_stub = types.ModuleType(
    "src.repositories.interactions.models.customer_leads_model"
)


class _CustomerLead:
    def __init__(self, **_kwargs):
        self.id = 1


customer_leads_model_stub.CustomerLead = _CustomerLead
sys.modules.setdefault(
    "src.repositories.interactions.models.customer_leads_model",
    customer_leads_model_stub,
)

chats_messages_model_stub = types.ModuleType(
    "src.repositories.interactions.models.chats_messages_model"
)


class _ChatMessage:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


chats_messages_model_stub.ChatsMessages = _ChatMessage
sys.modules.setdefault(
    "src.repositories.interactions.models.chats_messages_model",
    chats_messages_model_stub,
)

chats_messages_schema_stub = types.ModuleType(
    "src.repositories.interactions.schemas.chats_messages_schema"
)


class _ChatsMessagesCreate(SimpleNamespace):
    pass


chats_messages_schema_stub.ChatsMessagesCreate = _ChatsMessagesCreate
sys.modules.setdefault(
    "src.repositories.interactions.schemas.chats_messages_schema",
    chats_messages_schema_stub,
)

chats_model_stub = types.ModuleType("src.repositories.interactions.models.chats_model")


class _Chat:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


chats_model_stub.Chats = _Chat
sys.modules.setdefault(
    "src.repositories.interactions.models.chats_model",
    chats_model_stub,
)

crud_chats_stub = types.ModuleType("src.repositories.interactions.crud.chats_crud")


class _CRUDChat:
    def __init__(self) -> None:
        pass

    def get(self, _db, _phone, _store_phone):
        return None


crud_chats_stub.CRUDChat = _CRUDChat
sys.modules.setdefault(
    "src.repositories.interactions.crud.chats_crud",
    crud_chats_stub,
)

crud_chats_messages_stub = types.ModuleType(
    "src.repositories.interactions.crud.chats_messages_crud"
)


class _CRUDChatsMessages:
    def __init__(self) -> None:
        pass

    def get_recent_media_by_chat_id(self, _db, _chat_id, limit: int = 10):
        return []


crud_chats_messages_stub.CRUDChatsMessages = _CRUDChatsMessages
sys.modules.setdefault(
    "src.repositories.interactions.crud.chats_messages_crud",
    crud_chats_messages_stub,
)

crud_customer_leads_stub = types.ModuleType(
    "src.repositories.interactions.crud.customer_leads_crud"
)


class _CRUDCustomerLead:
    def __init__(self) -> None:
        pass


crud_customer_leads_stub.CRUDCustomerLead = _CRUDCustomerLead
sys.modules.setdefault(
    "src.repositories.interactions.crud.customer_leads_crud",
    crud_customer_leads_stub,
)

from src.models.user_models import InternalMessageModel
from src.services.chatbot import ChatBot


def _make_internal_message(
    *,
    phone: str = "5511999999999",
    store_phone: str = "5511888888888",
    when: datetime,
    content: str = "Olá",
    who_sent: str = "usr",
    send_to_wpp: bool = True,
    use_llm: bool = True,
) -> InternalMessageModel:
    return InternalMessageModel(
        phone=phone,
        store_phone=store_phone,
        last_interacted_at=when.isoformat(),
        content=content,
        content_link=None,
        type="text",
        who_sent=who_sent,
        pending_message="llm",
        additional_info=None,
        send_to_wpp=send_to_wpp,
        use_llm=use_llm,
    )


@pytest.fixture()
def chatbot_dependencies() -> dict[str, MagicMock]:
    chatbot_graph = MagicMock()
    chats_service = MagicMock()
    chats_service.upsert.return_value = 1
    chats_messages_service = MagicMock()
    customer_lead_service = MagicMock()
    whatsapp_client = MagicMock()

    return {
        "chatbot_graph": chatbot_graph,
        "chats_service": chats_service,
        "chats_messages_service": chats_messages_service,
        "customer_lead_service": customer_lead_service,
        "whatsapp_client": whatsapp_client,
    }


def test_human_cooldown_disables_llm(chatbot_dependencies: dict[str, MagicMock]) -> None:
    now = datetime.now(timezone.utc)
    last_message = _make_internal_message(when=now, who_sent="usr", use_llm=True)

    human_message = SimpleNamespace(
        sent_at=now - timedelta(minutes=3),
        content="Resposta humana",
    )

    deps = chatbot_dependencies
    deps["chats_messages_service"].create.return_value = SimpleNamespace()
    deps["chats_messages_service"].get_last_message_from_sender.side_effect = (
        lambda _db, _chat_id, who_sent: human_message if who_sent == "hum" else None
    )

    chatbot = ChatBot(**deps)

    response = chatbot.run(db=MagicMock(), data=[last_message])

    assert "pausada por 5 minutos" in response
    deps["chatbot_graph"].run.assert_not_called()
    deps["whatsapp_client"].send_message.assert_not_called()
    deps["chats_messages_service"].get_by_chat_id.assert_not_called()


def test_human_message_is_stored_even_without_llm(chatbot_dependencies: dict[str, MagicMock]) -> None:
    now = datetime.now(timezone.utc)
    human_message = _make_internal_message(
        when=now,
        who_sent="hum",
        send_to_wpp=False,
        use_llm=False,
    )

    deps = chatbot_dependencies
    deps["chats_messages_service"].get_last_message_from_sender.return_value = None

    chatbot = ChatBot(**deps)

    response = chatbot.run(db=MagicMock(), data=[human_message])

    assert "Mensagem de teste" in response
    deps["chats_messages_service"].create.assert_called_once()
    deps["chatbot_graph"].run.assert_not_called()


def test_duplicate_llm_echo_from_webhook_is_ignored(
    chatbot_dependencies: dict[str, MagicMock]
) -> None:
    now = datetime.now(timezone.utc)
    human_message = _make_internal_message(
        when=now,
        who_sent="hum",
        content="Olá cliente",
        send_to_wpp=False,
        use_llm=False,
    )

    last_llm = SimpleNamespace(
        sent_at=now - timedelta(seconds=5),
        content="Olá cliente",
    )

    deps = chatbot_dependencies

    def _get_last_sender(_db, _chat_id, who_sent):
        if who_sent == "llm":
            return last_llm
        return None

    deps["chats_messages_service"].get_last_message_from_sender.side_effect = (
        _get_last_sender
    )

    chatbot = ChatBot(**deps)

    chatbot.run(db=MagicMock(), data=[human_message])

    deps["chats_messages_service"].create.assert_not_called()
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
