"""FastAPI application."""

import argparse
import logging
from fastapi import FastAPI
from typing import Dict
import os

from src.controllers.user_controllers import user_router
from src.controllers.webhooks.evolution_controllers import evolution_router
from src.repositories.interactions.database import Base, engine
from src.repositories.interactions import models  # noqa: F401

from startup import create_mock_data


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("--docker", action="store_true", help="Running with docker")
parser.add_argument("--host", required=True, help="Application host.")
parser.add_argument("--port", required=True, help="Application port.")
parser.add_argument(
    "--reload",
    required=False,
    help="Enable auto-reload for development purposes.",
)
args = parser.parse_args()
if not args.docker:
    from dotenv import load_dotenv

    load_dotenv("../../.env")

ROOT_PATH_BACKEND = os.getenv("ROOT_PATH_BACKEND")

assert (
    ROOT_PATH_BACKEND is not None
), "Variable ROOT_PATH_BACKEND from env file shouldn't be None, fill in the credential."

logger.info("Creating database tables...")
Base.metadata.create_all(bind=engine)
logger.info("Database tables created successfully!")

logger.info("Populating mocked data!")
create_mock_data()

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS")

assert (
    ALLOWED_ORIGINS is not None
), "Variable ALLOWED_ORIGINS from env file shouldn't be None, fill in the credential."

logger.info("Starting FastAPI application...")
app = FastAPI(
    title="Technium API - Agents",
    root_path=ROOT_PATH_BACKEND,
    description="Documentação endpoints dos agentes da Technium",
)
app.include_router(user_router)
app.include_router(evolution_router)


@app.get("/", response_description="Api healthcheck")  # type: ignore[misc]
async def index() -> Dict[str, str]:
    """Define a route for handling HTTP GET requests to the root URL ("/")."""
    return {"0": "0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app", host=args.host, port=int(args.port), reload=(args.reload or False)
    )  # , log_level="trace")
