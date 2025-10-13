"""
Database configuration module.

Sets up the SQLAlchemy engine, session factory, and declarative base for ORM models.

Exports:
    - engine: SQLAlchemy database engine.
    - SessionLocal: Session factory for database interactions.
    - Base: Declarative base class for defining ORM models.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DB_URL = os.getenv("DATABASE_URL")
if DB_URL is None:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
