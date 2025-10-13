"""Context providers exposing store, customer, and lead details to the agent."""

from __future__ import annotations

from typing import Any, Dict, List

from ..base_context_providers import ContextProvider


def store_context_provider() -> ContextProvider:
    """Expose store metadata (name, numbers) to the agent."""

    def _provider(agent: Any, user_text: str) -> List[Dict[str, str]]:  # noqa: ARG001
        state = getattr(agent.memory, "state", {})
        store = state.get("store") if isinstance(state, dict) else None
        if not isinstance(store, dict) or not store:
            return []

        lines = ["Contexto da loja de móveis:"]
        name = store.get("name")
        if name:
            lines.append(f"- nome: {name}")
        info_number = store.get("info_forward_number")
        if info_number:
            lines.append(f"- numero_para_resumo: {info_number}")
        responsible = store.get("responsible_number")
        if responsible:
            lines.append(f"- numero_responsavel: {responsible}")
        entry = store.get("entry_phone")
        if entry:
            lines.append(f"- numero_atendimento: {entry}")
        contacts = store.get("routing_contacts")
        if isinstance(contacts, list) and contacts:
            lines.append("- contatos_disponiveis:")
            for contact in contacts:
                if not isinstance(contact, dict):
                    continue
                key = contact.get("key")
                name = contact.get("name")
                role = contact.get("role")
                phone = contact.get("display_phone") or contact.get("phone")
                parts = []
                if key:
                    parts.append(f"chave={key}")
                if name:
                    parts.append(f"nome={name}")
                if role:
                    parts.append(f"cargo={role}")
                if phone:
                    parts.append(f"telefone={phone}")
                if parts:
                    lines.append("  - " + ", ".join(parts))

        return [{"role": "system", "content": "\n".join(lines)}]

    return _provider


def customer_context_provider() -> ContextProvider:
    """Expose known customer details (phone, stored name)."""

    def _provider(agent: Any, user_text: str) -> List[Dict[str, str]]:  # noqa: ARG001
        state = getattr(agent.memory, "state", {})
        customer = state.get("customer") if isinstance(state, dict) else None
        if not isinstance(customer, dict) or not customer:
            return []

        lines = ["Contexto do cliente:"]
        phone = customer.get("phone")
        if phone:
            lines.append(f"- telefone: {phone}")
        name = customer.get("name")
        if name:
            lines.append(f"- nome: {name}")

        return [{"role": "system", "content": "\n".join(lines)}]

    return _provider


def lead_context_provider() -> ContextProvider:
    """Expose stored lead info, if the customer already exists in the CRM."""

    def _provider(agent: Any, user_text: str) -> List[Dict[str, str]]:  # noqa: ARG001
        state = getattr(agent.memory, "state", {})
        lead = state.get("lead") if isinstance(state, dict) else None
        if not isinstance(lead, dict) or not lead:
            return []

        lines = ["Dados já conhecidos do lead:"]
        if lead.get("name"):
            lines.append(f"- nome: {lead['name']}")
        if lead.get("phone"):
            lines.append(f"- telefone: {lead['phone']}")
        if lead.get("city"):
            lines.append(f"- cidade: {lead['city']}")
        if lead.get("product_interest"):
            lines.append(f"- interesse: {lead['product_interest']}")
        if lead.get("notes"):
            lines.append(f"- observacoes: {lead['notes']}")

        return [{"role": "system", "content": "\n".join(lines)}]

    return _provider
