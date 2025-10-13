"""Application settings loaded from environment variables.

Defines all environment-driven configuration used by the app.
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration model for the application."""

    REDIS_HOST: str
    REDIS_PASSWORD: str
    REDIS_SSL: bool
    CONSUMER_REDIS_TIME: int

    # PostgreSQL configuration
    POSTGRES_USER: str
    POSTGRES_HOST: str
    POSTGRES_DB: str
    POSTGRES_PASSWORD: str
    POSTGRES_PORT: int
    DATABASE_URL: str

    # LLM parameters
    OPENAI_API_KEY: str

    # Evolution API tokens
    EVOLUTION_API_URL: str
    EVOLUTION_API_KEY: str
    EVOLUTION_INSTANCE_NAME: str
    EVOLUTION_DEFAULT_DENTIST_PHONE: Optional[str] = None
    EVOLUTION_SESSION_PHONE_MAP: Optional[str] = None

    # API parameters
    ROOT_PATH_BACKEND: str
    ALLOWED_ORIGINS: list[str]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()  # type: ignore[call-arg]
