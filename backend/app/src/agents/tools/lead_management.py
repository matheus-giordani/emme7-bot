"""Tools for capturing furniture-store leads and notifying the team."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from src.agents.lib_agent.tool import ToolContext, tool
from src.repositories.interactions.crud.customer_leads_crud import CRUDCustomerLead
from src.repositories.interactions.database import SessionLocal
from src.repositories.interactions.schemas.customer_leads_schema import (
    CustomerLeadCreate,
    CustomerLeadUpdate,
)
from src.services.interactions.customer_leads_service import CustomerLeadService
from src.services.messaging.whatsapp.evolution_client import EvolutionClient
from src.services.store_routing import resolve_store_contact


def _get_evolution_client() -> EvolutionClient:
    base_url = os.getenv("EVOLUTION_API_URL")
    api_key = os.getenv("AUTHENTICATION_API_KEY")
    instance_name = os.getenv("EVOLUTION_INSTANCE_NAME")
    if not (base_url and api_key and instance_name):
        raise RuntimeError(
            "Credenciais do Evolution API não configuradas para uso da tool register_lead."
        )
    return EvolutionClient(base_url=base_url, api_key=api_key, instance_name=instance_name)


def _normalize_phone(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    return digits or None


class RegisterLeadInput(BaseModel):
    """Schema for registering a furniture-store lead."""

    customer_name: str = Field(..., description="Nome completo do cliente")
    customer_phone: Optional[str] = Field(None, description="Telefone/WhatsApp do cliente")
    customer_city: Optional[str] = Field(None, description="Cidade ou bairro do cliente")
    customer_email: Optional[str] = Field(None, description="E-mail do cliente")
    product_interest: Optional[str] = Field(None, description="Produto ou ambiente de interesse")
    budget_range: Optional[str] = Field(None, description="Faixa de orçamento informada")
    preferred_contact_time: Optional[str] = Field(
        None, description="Período preferido para contato"
    )
    notes: Optional[str] = Field(None, description="Observações adicionais relevantes")
    responsible_contact: Optional[str] = Field(
        default=None,
        description=(
            "Identificador opcional do contato interno que deve receber a notificação."
        ),
    )


@tool(
    name="register_lead",
    description=(
        "Salva dados do cliente interessado, envia o resumo para a loja e notifica o responsável."
    ),
    schema=RegisterLeadInput,
)
def register_lead(args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    """Persist the lead, forward the summary to internal numbers, and store context."""
    payload = RegisterLeadInput(**args)

    phone = _normalize_phone(payload.customer_phone) or ctx.memory.state.get("customer", {}).get("phone")  # type: ignore[index]
    if not phone:
        return {
            "ok": False,
            "message": "Telefone do cliente é obrigatório para registrar o lead.",
        }

    db = SessionLocal()
    repository = CRUDCustomerLead()
    service = CustomerLeadService(repository)
    try:
        lead_create = CustomerLeadCreate(
            name=payload.customer_name,
            phone=phone,
            email=payload.customer_email,
            city=payload.customer_city,
            preferred_contact_time=payload.preferred_contact_time,
            product_interest=payload.product_interest,
            notes=payload.notes,
        )
        lead = service.get_or_create(db, lead_create)

        update_data: Dict[str, Any] = {}
        if payload.customer_email and payload.customer_email != lead.email:
            update_data["email"] = payload.customer_email
        if payload.customer_city and payload.customer_city != lead.city:
            update_data["city"] = payload.customer_city
        if (
            payload.preferred_contact_time
            and payload.preferred_contact_time != lead.preferred_contact_time
        ):
            update_data["preferred_contact_time"] = payload.preferred_contact_time
        if payload.product_interest and payload.product_interest != lead.product_interest:
            update_data["product_interest"] = payload.product_interest
        if payload.notes and payload.notes != lead.notes:
            update_data["notes"] = payload.notes

        if update_data:
            lead = service.update(
                db,
                lead_id=lead.id,
                lead_update=CustomerLeadUpdate(**update_data),
            )

        summary_lines = [
            "Novo lead da loja de móveis:",
            f"Nome: {lead.name}",
            f"Telefone: {lead.phone}",
        ]
        if lead.city:
            summary_lines.append(f"Cidade/Bairro: {lead.city}")
        if lead.product_interest:
            summary_lines.append(f"Interesse: {lead.product_interest}")
        if lead.preferred_contact_time:
            summary_lines.append(
                f"Horário preferido: {lead.preferred_contact_time}"
            )
        if payload.budget_range:
            summary_lines.append(f"Orçamento: {payload.budget_range}")
        if lead.email:
            summary_lines.append(f"E-mail: {lead.email}")
        if lead.notes:
            summary_lines.append(f"Observações: {lead.notes}")
        summary = "\n".join(summary_lines)

        info_number = _normalize_phone(os.getenv("STORE_INFO_FORWARD_NUMBER"))
        responsible_number = _normalize_phone(os.getenv("STORE_RESPONSIBLE_NUMBER"))
        contact_override = resolve_store_contact(payload.responsible_contact)

        client = _get_evolution_client()
        errors: list[str] = []
        forwarded_contacts: list[Dict[str, Optional[str]]] = []

        if info_number:
            result = client.send_message(info_number, summary)
            if result.get("error"):
                errors.append(
                    f"Falha ao enviar resumo para {info_number}: {result['error']}"
                )
            else:
                forwarded_contacts.append(
                    {
                        "type": "summary",
                        "phone": info_number,
                        "label": "info_forward_number",
                    }
                )
        else:
            errors.append("Número de resumo da loja (STORE_INFO_FORWARD_NUMBER) não configurado.")

        targets: list[Dict[str, Optional[str]]] = []
        if contact_override is not None:
            targets.append(
                {
                    "phone": contact_override.phone,
                    "name": contact_override.name,
                    "role": contact_override.role,
                    "type": "responsible_contact",
                }
            )
        elif responsible_number:
            targets.append(
                {
                    "phone": responsible_number,
                    "name": None,
                    "role": None,
                    "type": "responsible_number",
                }
            )
        else:
            errors.append(
                "Número do responsável (STORE_RESPONSIBLE_NUMBER) não configurado."
            )

        if not targets and contact_override is None and payload.responsible_contact:
            errors.append(
                f"Contato '{payload.responsible_contact}' não encontrado em STORE_CONTACT_ROUTING."
            )

        for target in targets:
            phone = target.get("phone")
            if not phone:
                continue

            responsible_message = (
                "Novo cliente aguardando atendimento. "
                f"Dados: {lead.name} - {lead.phone}."
            )
            if lead.product_interest:
                responsible_message += f" Interesse: {lead.product_interest}."
            if lead.preferred_contact_time:
                responsible_message += (
                    f" Melhor horário: {lead.preferred_contact_time}."
                )
            if target.get("name"):
                responsible_message = (
                    f"Olá {target['name']}, " + responsible_message
                )

            result = client.send_message(phone, responsible_message)
            if result.get("error"):
                errors.append(
                    f"Falha ao notificar {phone}: {result['error']}"
                )
            else:
                forwarded_contacts.append(
                    {
                        "type": target.get("type"),
                        "phone": phone,
                        "label": target.get("name") or target.get("type"),
                        "role": target.get("role"),
                    }
                )

        ctx.memory.state.setdefault("lead", {})  # type: ignore[assignment]
        lead_state = ctx.memory.state["lead"]  # type: ignore[index]
        lead_state.update(
            {
                "id": lead.id,
                "name": lead.name,
                "phone": lead.phone,
                "city": lead.city,
                "product_interest": lead.product_interest,
                "notes": lead.notes,
            }
        )
        ctx.memory.state.setdefault("customer", {})  # type: ignore[assignment]
        ctx.memory.state["customer"]["name"] = lead.name  # type: ignore[index]

        return {
            "ok": not errors,
            "lead_id": lead.id,
            "forwarded_to": {
                "info_number": info_number,
                "responsible_number": responsible_number,
                "contacts": forwarded_contacts,
            },
            "errors": errors,
        }
    finally:
        db.close()
