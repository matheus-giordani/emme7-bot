"""Service layer helpers for customer leads."""

from typing import Optional
from fastapi import Depends
from sqlalchemy.orm import Session

from src.repositories.interactions.crud.customer_leads_crud import CRUDCustomerLead
from src.repositories.interactions.schemas.customer_leads_schema import (
    CustomerLeadCreate,
    CustomerLeadUpdate,
)
from src.repositories.interactions.models.customer_leads_model import CustomerLead


class CustomerLeadService:
    """Provide higher-level operations for store leads."""

    def __init__(self, repository: CRUDCustomerLead) -> None:
        self.repository = repository

    def get_or_create(self, db: Session, lead_in: CustomerLeadCreate) -> CustomerLead:
        existing = self.repository.get_by_phone(db, lead_in.phone)
        if existing:
            return existing
        return self.repository.create(db, lead_in)

    def update(
        self,
        db: Session,
        lead_id: int,
        lead_update: CustomerLeadUpdate,
    ) -> CustomerLead:
        lead = self.repository.get(db, lead_id)
        if lead is None:
            raise ValueError("Lead not found")
        return self.repository.update(db, lead, lead_update)

    def by_phone(self, db: Session, phone: str) -> Optional[CustomerLead]:
        return self.repository.get_by_phone(db, phone)


def get_customer_lead_service(
    repository: CRUDCustomerLead = Depends(),
) -> CustomerLeadService:
    return CustomerLeadService(repository)
