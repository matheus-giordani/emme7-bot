"""Module for interacting with a Redis database to store, retrieve, and delete messages."""

import json
import logging
import redis
from typing import Dict, List, Any, Tuple, Union
from src.models.user_models import InternalMessageModel

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def str_to_bool(value: str) -> bool:
    """Convert REDIS_SSL env variable to boolean."""
    return value.lower() in ("true", "1", "yes")


class RedisDatabase:
    """Handles operations with the Redis database for storing and retrieving messages."""

    def __init__(
        self, host: str, port: int, password: str, ssl: Union[str, bool]
    ) -> None:
        """
        Initialize a connection to the Redis database.

        Args:
            host (str): The hostname or IP address of the Redis server.
            port (int): The port number of the Redis server (default is 6379).

        This method creates a Redis connection using the provided host and port,
        and initializes the `handler` attribute to interact with the Redis database.
        """
        ssl = str_to_bool(ssl) if isinstance(ssl, str) else ssl
        try:
            self.handler = redis.Redis(
                host=host,
                port=port,
                password=password,
                ssl=ssl,
                db=0,
                ssl_cert_reqs=None,
            )
        except Exception as e:
            logger.info(f"################## error: {e} ##################")

    def save(self, data: InternalMessageModel, datetime_now: float) -> None:
        """Save data with a timestamp to Redis sorted set."""
        data_dict = data.model_dump()
        self.handler.zadd("webhook", {json.dumps(data_dict): datetime_now})
        logging.info(f"Saved message: {data_dict}")

    def retrieve_messages(self) -> List[Tuple[bytes, float]]:
        """Retrieve messages from webhook table."""
        messages = self.handler.zrange("webhook", 0, -1, withscores=True)
        return messages  # type: ignore

    def delete_message(self, message: Dict[str, Any]) -> None:
        """Delete messages from Redis."""
        self.handler.zrem("webhook", json.dumps(message))
        logging.info(f"Deleted message: {message}")
