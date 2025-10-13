"""CRUD helpers for customer leads."""

from typing import Optional
from sqlalchemy.orm import Session

from src.repositories.interactions.models.customer_leads_model import CustomerLead
from src.repositories.interactions.schemas.customer_leads_schema import (
    CustomerLeadCreate,
    CustomerLeadUpdate,
)


class CRUDCustomerLead:
    """Database access for customer leads."""

    def get_by_phone(self, db: Session, phone: str) -> Optional[CustomerLead]:
        return db.query(CustomerLead).filter(CustomerLead.phone == phone).first()

    def get(self, db: Session, lead_id: int) -> Optional[CustomerLead]:
        return db.query(CustomerLead).filter(CustomerLead.id == lead_id).first()

    def create(self, db: Session, lead_in: CustomerLeadCreate) -> CustomerLead:
        lead = CustomerLead(**lead_in.model_dump())
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead

    def update(
        self,
        db: Session,
        lead: CustomerLead,
        lead_update: CustomerLeadUpdate,
    ) -> CustomerLead:
        data = lead_update.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(lead, field, value)
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead
