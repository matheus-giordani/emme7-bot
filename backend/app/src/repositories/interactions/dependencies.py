"""
Database session dependency.

Provides a SQLAlchemy database session for use in request handling.
Ensures proper cleanup after use.
"""

from src.repositories.interactions.database import SessionLocal
from typing import Generator


def get_db() -> Generator[SessionLocal, None, None]:
    """
    Yield a database session and ensures it is closed after use.

    This function is typically used as a FastAPI dependency to provide
    a database session per request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
