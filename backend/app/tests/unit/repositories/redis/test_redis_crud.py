"""Test Redis CRUD."""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.modules.setdefault("redis", MagicMock())

from src.repositories.redis.redis_crud import RedisDatabase
from src.models.user_models import InternalMessageModel


class TestRedisCrud:
    """Test cases for RedisDatabase class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.test_host = "test_host"
        self.test_port = 6379
        self.test_password = "test_password"
        self.test_ssl = "true"
        self.test_data = InternalMessageModel(
            phone="553112345678",
            store_phone="553198765432",
            last_interacted_at="2025-06-04 20:48:42.154852+00:00",
            content="Oi!",
            content_link=None,
            type="text",
            who_sent="usr",
            send_to_wpp=False,
            use_llm=False,
        )

    def test_init_creates_redis_connection(self) -> None:
        """Test that __init__ creates a Redis connection with correct parameters."""
        with patch("redis.Redis") as MockRedis:
            mock_redis_instance = MagicMock()
            MockRedis.return_value = mock_redis_instance

            # Act
            redis_db = RedisDatabase(
                self.test_host, self.test_port, self.test_password, self.test_ssl
            )

            # Assert
            MockRedis.assert_called_once_with(
                host=self.test_host,
                port=self.test_port,
                password=self.test_password,
                ssl=True,  # str_to_bool converts "true" to True
                db=0,
                ssl_cert_reqs=None,
            )
            assert redis_db.handler == mock_redis_instance

    def test_save_adds_data_to_redis_and_logs(self) -> None:
        """Test that save method adds data to Redis and logs the operation."""
        data_dict = self.test_data.model_dump()
        datetime_now = 1749215669.57257

        with patch("redis.Redis") as MockRedis, patch(
            "src.repositories.redis.redis_crud.logging.info"
        ) as mock_log:
            mock_redis_instance = MagicMock()
            MockRedis.return_value = mock_redis_instance
            storage = RedisDatabase(
                self.test_host, self.test_port, self.test_password, self.test_ssl
            )

            # Act
            storage.save(self.test_data, datetime_now)

            # Assert zadd was called with correct parameters
            args, kwargs = mock_redis_instance.zadd.call_args
            assert args[0] == "webhook"

            zadd_data = args[1]
            assert json.dumps(data_dict) in zadd_data
            assert zadd_data[json.dumps(data_dict)] == 1749215669.57257

            # Assert logging was called
            mock_log.assert_called_once_with(f"Saved message: {data_dict}")

    def test_save_with_different_data_types(self) -> None:
        """Test save method with different data types and edge cases."""
        # Test with None values
        data_with_none = InternalMessageModel(
            phone="553112345678",
            store_phone="553198765432",
            last_interacted_at="2025-06-04 20:48:42.154852+00:00",
            content=None,
            content_link=None,
            type="text",
            who_sent="usr",
            send_to_wpp=False,
            use_llm=False,
        )

        with patch("redis.Redis") as MockRedis:
            mock_redis_instance = MagicMock()
            MockRedis.return_value = mock_redis_instance
            storage = RedisDatabase(
                self.test_host, self.test_port, self.test_password, self.test_ssl
            )

            # Act
            storage.save(data_with_none, 1749215669.57257)

            # Assert
            args, kwargs = mock_redis_instance.zadd.call_args
            assert args[0] == "webhook"

            zadd_data = args[1]
            data_dict = data_with_none.model_dump()
            assert json.dumps(data_dict) in zadd_data

    def test_retrieve_messages_returns_messages_from_redis(self) -> None:
        """Test that retrieve_messages returns messages from Redis webhook table."""
        expected_messages = [
            (
                b'{"phone": "553112345678", "store_phone": "553198765432", "last_interacted_at": "2025-06-04 20:48:42.154852+00:00", "content": "Oi!", "content_link": null, "type": "text", "who_sent": "usr", "pending_message": null, "additional_info": null, "send_to_wpp": true}',
                1749215669.57257,
            ),
            (
                b'{"phone": "553198765432", "store_phone": "553112345678", "last_interacted_at": "2025-06-04 21:00:00.000000+00:00", "content": "Hello", "content_link": null, "type": "text", "who_sent": "llm", "pending_message": null, "additional_info": null, "send_to_wpp": true}',
                1749216000.00000,
            ),
        ]

        with patch("redis.Redis") as MockRedis:
            mock_redis_instance = MagicMock()
            mock_redis_instance.zrange.return_value = expected_messages
            MockRedis.return_value = mock_redis_instance
            storage = RedisDatabase(
                self.test_host, self.test_port, self.test_password, self.test_ssl
            )

            # Act
            result = storage.retrieve_messages()

            # Assert
            mock_redis_instance.zrange.assert_called_once_with(
                "webhook", 0, -1, withscores=True
            )
            assert result == expected_messages

    def test_retrieve_messages_returns_empty_list_when_no_messages(self) -> None:
        """Test that retrieve_messages returns empty list when no messages exist."""
        with patch("redis.Redis") as MockRedis:
            mock_redis_instance = MagicMock()
            mock_redis_instance.zrange.return_value = []
            MockRedis.return_value = mock_redis_instance
            storage = RedisDatabase(
                self.test_host, self.test_port, self.test_password, self.test_ssl
            )

            # Act
            result = storage.retrieve_messages()

            # Assert
            assert result == []
            mock_redis_instance.zrange.assert_called_once_with(
                "webhook", 0, -1, withscores=True
            )

    def test_delete_message_removes_message_from_redis_and_logs(self) -> None:
        """Test that delete_message removes message from Redis and logs the operation."""
        message_to_delete = {
            "phone": "553112345678",
            "store_phone": "553198765432",
            "last_interacted_at": "2025-06-04 20:48:42.154852+00:00",
            "content": "Oi!",
            "content_link": None,
            "type": "text",
            "who_sent": "usr",
            "pending_message": None,
            "additional_info": None,
            "send_to_wpp": True,
        }

        with patch("redis.Redis") as MockRedis, patch(
            "src.repositories.redis.redis_crud.logging.info"
        ) as mock_log:
            mock_redis_instance = MagicMock()
            MockRedis.return_value = mock_redis_instance
            storage = RedisDatabase(
                self.test_host, self.test_port, self.test_password, self.test_ssl
            )

            # Act
            storage.delete_message(message_to_delete)

            # Assert
            mock_redis_instance.zrem.assert_called_once_with(
                "webhook", json.dumps(message_to_delete)
            )
            mock_log.assert_called_once_with(f"Deleted message: {message_to_delete}")

    def test_delete_message_with_complex_message(self) -> None:
        """Test delete_message with complex message containing special characters."""
        complex_message = {
            "phone": "553112345678",
            "store_phone": "553198765432",
            "last_interacted_at": "2025-06-04 20:48:42.154852+00:00",
            "content": "Hello! How are you? 😊",
            "content_link": "https://example.com/image.jpg",
            "type": "image",
            "who_sent": "usr",
            "pending_message": None,
            "additional_info": None,
            "send_to_wpp": True,
        }

        with patch("redis.Redis") as MockRedis:
            mock_redis_instance = MagicMock()
            MockRedis.return_value = mock_redis_instance
            storage = RedisDatabase(
                self.test_host, self.test_port, self.test_password, self.test_ssl
            )

            # Act
            storage.delete_message(complex_message)

            # Assert
            mock_redis_instance.zrem.assert_called_once_with(
                "webhook", json.dumps(complex_message)
            )

    def test_delete_message_with_empty_message(self) -> None:
        """Test delete_message with empty message dictionary."""
        empty_message: dict[str, str | int | bool | None] = {}

        with patch("redis.Redis") as MockRedis:
            mock_redis_instance = MagicMock()
            MockRedis.return_value = mock_redis_instance
            storage = RedisDatabase(
                self.test_host, self.test_port, self.test_password, self.test_ssl
            )

            # Act
            storage.delete_message(empty_message)

            # Assert
            mock_redis_instance.zrem.assert_called_once_with(
                "webhook", json.dumps(empty_message)
            )

    def test_integration_save_and_retrieve(self) -> None:
        """Integration test to verify save and retrieve work together."""
        with patch("redis.Redis") as MockRedis:
            mock_redis_instance = MagicMock()
            MockRedis.return_value = mock_redis_instance
            storage = RedisDatabase(
                self.test_host, self.test_port, self.test_password, self.test_ssl
            )

            # Save a message
            storage.save(self.test_data, 1749215669.57257)

            # Mock the retrieve to return what we just saved
            expected_messages = [
                (json.dumps(self.test_data.model_dump()).encode(), 1749215669.57257)
            ]
            mock_redis_instance.zrange.return_value = expected_messages

            # Retrieve messages
            result = storage.retrieve_messages()

            # Assert
            assert result == expected_messages
            assert len(result) == 1
            assert result[0][1] == 1749215669.57257

    def test_save_with_different_timestamps(self) -> None:
        """Test save method with different timestamp values."""
        timestamps = [0.0, 1749215669.57257, 9999999999.99999]

        with patch("redis.Redis") as MockRedis:
            mock_redis_instance = MagicMock()
            MockRedis.return_value = mock_redis_instance
            storage = RedisDatabase(
                self.test_host, self.test_port, self.test_password, self.test_ssl
            )

            for timestamp in timestamps:
                # Act
                storage.save(self.test_data, timestamp)

                # Assert
                args, kwargs = mock_redis_instance.zadd.call_args
                assert args[0] == "webhook"

                zadd_data = args[1]
                data_dict = self.test_data.model_dump()
                assert json.dumps(data_dict) in zadd_data
                assert zadd_data[json.dumps(data_dict)] == timestamp

    def test_redis_connection_error_handling(self) -> None:
        """Test that Redis connection errors are properly handled."""
        with patch("redis.Redis") as MockRedis, patch(
            "src.repositories.redis.redis_crud.logger.info"
        ) as mock_log:
            # Simulate Redis connection error
            MockRedis.side_effect = Exception("Redis connection failed")

            # Act
            redis_db = RedisDatabase(
                self.test_host, self.test_port, self.test_password, self.test_ssl
            )

            # Assert
            # The exception should be caught and logged, not raised
            mock_log.assert_called_once_with(
                "################## error: Redis connection failed ##################"
            )
            # The handler should not be set when connection fails
            assert not hasattr(redis_db, "handler")

    def test_zadd_error_handling(self) -> None:
        """Test that zadd errors are properly handled."""
        with patch("redis.Redis") as MockRedis:
            mock_redis_instance = MagicMock()
            mock_redis_instance.zadd.side_effect = Exception("Redis zadd failed")
            MockRedis.return_value = mock_redis_instance
            storage = RedisDatabase(
                self.test_host, self.test_port, self.test_password, self.test_ssl
            )

            # Act & Assert
            with pytest.raises(Exception, match="Redis zadd failed"):
                storage.save(self.test_data, 1749215669.57257)

    def test_zrange_error_handling(self) -> None:
        """Test that zrange errors are properly handled."""
        with patch("redis.Redis") as MockRedis:
            mock_redis_instance = MagicMock()
            mock_redis_instance.zrange.side_effect = Exception("Redis zrange failed")
            MockRedis.return_value = mock_redis_instance
            storage = RedisDatabase(
                self.test_host, self.test_port, self.test_password, self.test_ssl
            )

            # Act & Assert
            with pytest.raises(Exception, match="Redis zrange failed"):
                storage.retrieve_messages()

    def test_zrem_error_handling(self) -> None:
        """Test that zrem errors are properly handled."""
        message_to_delete = {"test": "message"}

        with patch("redis.Redis") as MockRedis:
            mock_redis_instance = MagicMock()
            mock_redis_instance.zrem.side_effect = Exception("Redis zrem failed")
            MockRedis.return_value = mock_redis_instance
            storage = RedisDatabase(
                self.test_host, self.test_port, self.test_password, self.test_ssl
            )

            # Act & Assert
            with pytest.raises(Exception, match="Redis zrem failed"):
                storage.delete_message(message_to_delete)
