"""Seed helper for local development."""

import logging
from sqlalchemy.orm import Session

from src.repositories.interactions.database import SessionLocal
from src.repositories.interactions.models.customer_leads_model import CustomerLead

logger = logging.getLogger(__name__)


def create_mock_data() -> None:
    """Populate the database with example leads when empty."""
    db: Session = SessionLocal()
    try:
        existing = db.query(CustomerLead).count()
        if existing:
            logger.info("Mock leads already present (%d records). Skipping.", existing)
            return

        logger.info("Creating demo customer leads for furniture store flows.")
        sample_leads = [
            {
                "name": "João Pereira",
                "phone": "55999990001",
                "email": "joao@example.com",
                "city": "Maceió",
                "product_interest": "Sofá retrátil",
                "notes": "Prefere contato no período da tarde.",
            },
            {
                "name": "Marta Silva",
                "phone": "55999990002",
                "email": "marta@example.com",
                "city": "Recife",
                "product_interest": "Mesa de jantar 6 lugares",
            },
        ]
        for lead in sample_leads:
            db.add(CustomerLead(**lead))
        db.commit()
        logger.info("Demo leads inserted with success.")
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to seed mock leads: %s", exc)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":  # pragma: no cover
    create_mock_data()
