"""Pydantic schemas for customer leads."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, StringConstraints
from typing import Annotated


class CustomerLeadBase(BaseModel):
    """Shared attributes for customer leads."""

    name: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    phone: Annotated[str, StringConstraints(min_length=8, max_length=20)]
    email: Optional[Annotated[str, StringConstraints(max_length=160)]] = None
    city: Optional[Annotated[str, StringConstraints(max_length=120)]] = None
    preferred_contact_time: Optional[
        Annotated[str, StringConstraints(max_length=32)]
    ] = None
    product_interest: Optional[
        Annotated[str, StringConstraints(max_length=160)]
    ] = None
    notes: Optional[str] = None
    forwarded_to: Optional[Annotated[str, StringConstraints(max_length=20)]] = None


class CustomerLeadCreate(CustomerLeadBase):
    """Payload required to create a new lead."""

    pass


class CustomerLeadUpdate(BaseModel):
    """Fields allowed to update for an existing lead."""

    name: Optional[Annotated[str, StringConstraints(min_length=1, max_length=120)]] = None
    email: Optional[Annotated[str, StringConstraints(max_length=160)]] = None
    city: Optional[Annotated[str, StringConstraints(max_length=120)]] = None
    preferred_contact_time: Optional[
        Annotated[str, StringConstraints(max_length=32)]
    ] = None
    product_interest: Optional[
        Annotated[str, StringConstraints(max_length=160)]
    ] = None
    notes: Optional[str] = None
    forwarded_to: Optional[Annotated[str, StringConstraints(max_length=20)]] = None


class CustomerLeadResponse(CustomerLeadBase):
    """Response model for a stored lead."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {
        "from_attributes": True,
    }
