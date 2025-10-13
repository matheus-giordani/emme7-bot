"""SQLAlchemy model for customer leads captured by the furniture store bot."""

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from src.repositories.interactions.database import Base


class CustomerLead(Base):  # type: ignore[misc]
    """Represents a potential customer interested in furniture products."""

    __tablename__ = "customer_leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(160), nullable=True)
    city = Column(String(120), nullable=True)
    preferred_contact_time = Column(String(32), nullable=True)
    product_interest = Column(String(160), nullable=True)
    notes = Column(Text, nullable=True)
    forwarded_to = Column(String(20), nullable=True)
    created_at = Column(TIMESTAMP(timezone=False), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=False), nullable=True, onupdate=func.now()
    )

    __mapper_args__ = {"eager_defaults": True}
