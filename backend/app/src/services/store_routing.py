"""Utilities for routing leads to store contacts configured via environment."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


CONTACT_ENV = "STORE_CONTACT_ROUTING"


def _normalize_identifier(value: str) -> str:
    """Normalize identifiers (keys, names) for case-insensitive matching."""

    cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower())
    return cleaned.strip("_")


def _normalize_phone(value: Optional[str]) -> Optional[str]:
    """Return only the digits from a phone string."""

    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    return digits or None


@dataclass(frozen=True)
class StoreContact:
    """Represents a contact available for lead routing."""

    key: str
    name: str
    phone: str
    role: Optional[str] = None
    display_phone: Optional[str] = None

    def as_dict(self) -> Dict[str, Optional[str]]:
        """Return a serializable representation for context providers."""

        return {
            "key": self.key,
            "name": self.name,
            "phone": self.phone,
            "role": self.role,
            "display_phone": self.display_phone or self.phone,
        }


def _iter_raw_contacts(raw: str) -> Iterable[StoreContact]:
    """Yield contacts parsed from the environment string."""

    if not raw:
        return []

    contacts: List[StoreContact] = []
    for chunk in raw.split(";"):
        entry = chunk.strip()
        if not entry:
            continue

        parts = [part.strip() for part in entry.split(":") if part.strip()]
        if len(parts) < 3:
            continue

        key, name, phone, *rest = parts
        normalized_phone = _normalize_phone(phone)
        if not normalized_phone:
            continue

        role = rest[0] if rest else None
        contact = StoreContact(
            key=_normalize_identifier(key),
            name=name,
            phone=normalized_phone,
            role=role,
            display_phone=phone,
        )
        contacts.append(contact)

    return contacts


_CACHE_RAW: Optional[str] = None
_CACHE_CONTACTS: List[StoreContact] = []
_CACHE_LOOKUP: Dict[str, StoreContact] = {}


def _ensure_cache() -> None:
    """Load and cache contacts if the environment has changed."""

    global _CACHE_RAW, _CACHE_CONTACTS, _CACHE_LOOKUP

    current_raw = os.getenv(CONTACT_ENV, "")
    if current_raw == _CACHE_RAW:
        return

    contacts = list(_iter_raw_contacts(current_raw))
    lookup: Dict[str, StoreContact] = {}

    for contact in contacts:
        aliases = {
            contact.key,
            _normalize_identifier(contact.name),
        }
        if contact.role:
            aliases.add(_normalize_identifier(contact.role))

        for alias in aliases:
            lookup[alias] = contact

    _CACHE_RAW = current_raw
    _CACHE_CONTACTS = contacts
    _CACHE_LOOKUP = lookup


def get_store_contacts() -> List[StoreContact]:
    """Return the list of configured store contacts."""

    _ensure_cache()
    return list(_CACHE_CONTACTS)


def resolve_store_contact(identifier: Optional[str]) -> Optional[StoreContact]:
    """Resolve a contact given a key, name or role string."""

    if not identifier:
        return None

    _ensure_cache()
    normalized = _normalize_identifier(identifier)
    if not normalized:
        return None

    return _CACHE_LOOKUP.get(normalized)

