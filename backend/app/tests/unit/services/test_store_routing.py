import importlib
import os

import pytest


@pytest.fixture()
def store_routing_module(monkeypatch):
    monkeypatch.setenv(
        "STORE_CONTACT_ROUTING",
        "orcamento:Davi:55 19 4413-660:Assistente Tecnico;"
        "assistencia_tecnica:Tatiane:5581 8221 1659:Lider de Projetos",
    )
    from src.services import store_routing  # type: ignore

    importlib.reload(store_routing)
    yield store_routing

    monkeypatch.delenv("STORE_CONTACT_ROUTING", raising=False)
    importlib.reload(store_routing)


def test_get_store_contacts_parses_entries(store_routing_module):
    contacts = store_routing_module.get_store_contacts()
    assert len(contacts) == 2
    keys = {contact.key for contact in contacts}
    assert keys == {"orcamento", "assistencia_tecnica"}


def test_resolve_store_contact_matches_by_name(store_routing_module):
    contact = store_routing_module.resolve_store_contact("Tatiane")
    assert contact is not None
    assert contact.phone == "558182211659"
    assert contact.key == "assistencia_tecnica"
