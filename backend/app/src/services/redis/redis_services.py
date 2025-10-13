"""Module for saving user messages to a Redis database."""

import os
import json
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Any, Union
from src.repositories.redis.redis_crud import RedisDatabase
from src.models.user_models import InternalMessageModel

redis_handler = RedisDatabase(
    host=os.getenv("REDIS_HOST"),
    password=os.getenv("REDIS_PASSWORD"),
    port=6379,
    ssl=os.getenv("REDIS_SSL"),
)


class RedisService:
    """Treats data related to a Redis database for storing and retrieving messages."""

    def __init__(self, redis_repository: RedisDatabase) -> None:
        """Initialize the redis service with the redis repository."""
        self.redis_repository = redis_repository

    def save(self, data: InternalMessageModel) -> None:
        """
        Save a InternalMessageModel object to the Redis database.

        Args:
            data (InternalMessageModel): The InternalMessageModel object containing the data to be saved.
        """
        datetime_now = datetime.timestamp(datetime.now(timezone.utc))
        self.redis_repository.save(data, datetime_now)

    def retrieve_messages(self) -> List[Tuple[bytes, float]]:
        """Retrieve messages from webhook table."""
        messages: List[Tuple[bytes, float]] = self.redis_repository.retrieve_messages()
        return messages

    def delete_messages(self, messages: List[Dict[str, Any]]) -> None:
        """Delete messages from Redis."""
        for message in messages:
            self.redis_repository.delete_message(message)

    def group_messages(
        self, messages: List[Tuple[bytes, float]]
    ) -> Dict[int, Dict[str, List[Tuple[InternalMessageModel, float]]]]:
        """Retrieve messages older than the specified time threshold.

        Args:

        Returns:
            Dict[int, Dict[str, List[Tuple[InternalMessageModel, float]]]]: A nested dictionary where:
                - The outermost key (`int`) represents the client ID.
                - The inner key (`str`) represents the client's phone number which received/sent the message.
                - The value is a list of tuples, each containing:
                    - A `InternalMessageModel` instance.
                    - A `float` representing the unix timestamp of when the message was registered in Redis.
        """
        grouped = defaultdict(lambda: defaultdict(list))  # type:ignore
        for raw_bytes, redis_unixtimestamp in messages:
            item = json.loads(raw_bytes.decode("utf-8"))
            grouped[item["store_phone"]][item["phone"]].append(
                (InternalMessageModel(**item), redis_unixtimestamp)
            )
        result = {k: dict(v) for k, v in grouped.items()}
        return result

    def filter_messages(
        self,
        grouped_messages: Dict[
            int, Dict[str, List[Tuple[InternalMessageModel, float]]]
        ],
        cut: float,
    ) -> Any:
        """Filter messages from grouped_messages which are older than the timestamp 'cut'."""
        filtered_messages = []
        for store_phone, messages_by_phone in grouped_messages.items():
            for phone, messages in messages_by_phone.items():
                messages.sort(key=lambda x: x[1])
                if messages[-1][1] < cut:
                    filtered_messages.extend([msg[0] for msg in messages])

        return filtered_messages

    def time_search(self, time_threshold_seconds: int = 60) -> Any:
        """Retrieve messages older than the specified time threshold."""
        messages = self.retrieve_messages()
        grouped_messages = self.group_messages(messages)

        threshold = datetime.now(timezone.utc) - timedelta(
            seconds=time_threshold_seconds
        )
        cut = datetime.timestamp(threshold)
        filtered_messages = self.filter_messages(grouped_messages, cut)

        return filtered_messages


# Dependency for FastAPI
def create_redis_service(
    host: str, port: int, password: str, ssl: Union[str, bool]
) -> RedisService:
    """Retrieve an instance of RedisService."""
    redis_repository = RedisDatabase(host, port, password, ssl)
    return RedisService(redis_repository)
