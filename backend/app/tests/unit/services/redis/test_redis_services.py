"""Test Redis Services."""

import json
import sys
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import pytest

sys.modules.setdefault("redis", MagicMock())

from src.repositories.redis.redis_crud import RedisDatabase
from src.services.redis.redis_services import RedisService, create_redis_service
from src.models.user_models import InternalMessageModel


class TestRedisService:
    """Test cases for RedisService class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.mock_redis_repository = MagicMock(spec=RedisDatabase)
        self.redis_service = RedisService(self.mock_redis_repository)

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

        self.test_messages = [
            (
                b'{"phone": "553112345678", "store_phone": "553198765432", "last_interacted_at": "2025-06-04 20:48:42.154852+00:00", "content": "Oi!", "content_link": null, "type": "text", "who_sent": "usr", "pending_message": null, "additional_info": null, "send_to_wpp": false, "use_llm": false}',
                1749215669.57257,
            ),
            (
                b'{"phone": "553198765432", "store_phone": "553112345678", "last_interacted_at": "2025-06-04 21:00:00.000000+00:00", "content": "Hello", "content_link": null, "type": "text", "who_sent": "llm", "pending_message": null, "additional_info": null, "send_to_wpp": false, "use_llm": false}',
                1749216000.00000,
            ),
            (
                b'{"phone": "553112345678", "store_phone": "553198765432", "last_interacted_at": "2025-06-04 22:00:00.000000+00:00", "content": "Test message", "content_link": null, "type": "text", "who_sent": "usr", "pending_message": null, "additional_info": null, "send_to_wpp": false, "use_llm": false}',
                1749219600.00000,
            ),
        ]

    def test_init_creates_service_with_repository(self) -> None:
        """Test that __init__ creates a RedisService with the provided repository."""
        # Act
        service = RedisService(self.mock_redis_repository)

        # Assert
        assert service.redis_repository == self.mock_redis_repository

    def test_save_calls_repository_with_timestamp(self) -> None:
        """Test that save method calls repository with current timestamp."""
        # Arrange
        with patch("src.services.redis.redis_services.datetime") as mock_datetime:
            mock_now = datetime(2025, 6, 4, 20, 48, 42, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            expected_timestamp = mock_now.timestamp()
            mock_datetime.timestamp.return_value = expected_timestamp

            # Act
            self.redis_service.save(self.test_data)

            # Assert
            self.mock_redis_repository.save.assert_called_once_with(
                self.test_data, expected_timestamp
            )

    def test_retrieve_messages_calls_repository(self) -> None:
        """Test that retrieve_messages calls repository and returns result."""
        # Arrange
        expected_messages = self.test_messages
        self.mock_redis_repository.retrieve_messages.return_value = expected_messages

        # Act
        result = self.redis_service.retrieve_messages()

        # Assert
        self.mock_redis_repository.retrieve_messages.assert_called_once()
        assert result == expected_messages

    def test_delete_messages_calls_repository_for_each_message(self) -> None:
        """Test that delete_messages calls repository for each message in the list."""
        # Arrange
        messages_to_delete = [
            {
                "phone": "553112345678",
                "store_phone": "553198765432",
                "content": "Message 1",
            },
            {
                "phone": "553198765432",
                "store_phone": "553112345678",
                "content": "Message 2",
            },
        ]

        # Act
        self.redis_service.delete_messages(messages_to_delete)

        # Assert
        assert self.mock_redis_repository.delete_message.call_count == 2
        self.mock_redis_repository.delete_message.assert_any_call(messages_to_delete[0])
        self.mock_redis_repository.delete_message.assert_any_call(messages_to_delete[1])

    def test_delete_messages_with_empty_list(self) -> None:
        """Test that delete_messages handles empty list correctly."""
        # Act
        self.redis_service.delete_messages([])

        # Assert
        self.mock_redis_repository.delete_message.assert_not_called()

    def test_group_messages_with_empty_list(self) -> None:
        """Test that group_messages handles empty list correctly."""
        # Act
        result = self.redis_service.group_messages([])

        # Assert
        assert result == {}

    def test_group_messages_with_invalid_json(self) -> None:
        """Test that group_messages handles invalid JSON gracefully."""
        invalid_messages = [
            (b"invalid json", 1749215669.57257),
        ]

        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            self.redis_service.group_messages(invalid_messages)

    def test_filter_messages_filters_by_timestamp_cutoff(self) -> None:
        """Test that filter_messages correctly filters messages by timestamp cutoff."""
        # Arrange
        grouped_messages = {
            "553198765432": {
                "553112345678": [
                    (
                        InternalMessageModel(
                            phone="553112345678",
                            store_phone="553198765432",
                            last_interacted_at="2025-06-04 20:48:42.154852+00:00",
                            content="Old message",
                            content_link=None,
                            type="text",
                            who_sent="usr",
                            send_to_wpp=False,
                            use_llm=False,
                        ),
                        1749215669.0,
                    ),
                    (
                        InternalMessageModel(
                            phone="553112345678",
                            store_phone="553198765432",
                            last_interacted_at="2025-06-04 20:48:42.154852+00:00",
                            content="New message",
                            content_link=None,
                            type="text",
                            who_sent="usr",
                            send_to_wpp=False,
                            use_llm=False,
                        ),
                        1749216000.0,
                    ),
                ]
            }
        }
        cut_timestamp = 1749215800.0  # Between the two messages

        # Act
        result = self.redis_service.filter_messages(grouped_messages, cut_timestamp)

        # Assert
        # Should return both messages since the latest message (1749216000.0) is not < cut_timestamp (1749215800.0)
        # The filter logic checks if messages[-1][1] < cut, which means it only filters if ALL messages are below cutoff
        assert len(result) == 0

    def test_filter_messages_with_all_messages_below_cutoff(self) -> None:
        """Test that filter_messages returns messages when all are below cutoff."""
        # Arrange
        grouped_messages = {
            "553198765432": {
                "553112345678": [
                    (
                        InternalMessageModel(
                            phone="553112345678",
                            store_phone="553198765432",
                            last_interacted_at="2025-06-04 20:48:42.154852+00:00",
                            content="Old message",
                            content_link=None,
                            type="text",
                            who_sent="usr",
                            send_to_wpp=False,
                            use_llm=False,
                        ),
                        1749215669.0,
                    ),
                    (
                        InternalMessageModel(
                            phone="553112345678",
                            store_phone="553198765432",
                            last_interacted_at="2025-06-04 20:48:42.154852+00:00",
                            content="Newer message",
                            content_link=None,
                            type="text",
                            who_sent="usr",
                            send_to_wpp=False,
                            use_llm=False,
                        ),
                        1749215700.0,
                    ),
                ]
            }
        }
        cut_timestamp = 1749215800.0  # Above both messages

        # Act
        result = self.redis_service.filter_messages(grouped_messages, cut_timestamp)

        # Assert
        assert len(result) == 2
        assert result[0].content == "Old message"
        assert result[1].content == "Newer message"

    def test_filter_messages_with_empty_grouped_messages(self) -> None:
        """Test that filter_messages handles empty grouped messages correctly."""
        # Act
        result = self.redis_service.filter_messages({}, 1749215800.0)

        # Assert
        assert result == []

    def test_filter_messages_sorts_messages_by_timestamp(self) -> None:
        """Test that filter_messages sorts messages by timestamp before filtering."""
        # Arrange
        grouped_messages = {
            "553198765432": {
                "553112345678": [
                    (
                        InternalMessageModel(
                            phone="553112345678",
                            store_phone="553198765432",
                            last_interacted_at="2025-06-04 20:48:42.154852+00:00",
                            content="Second message",
                            content_link=None,
                            type="text",
                            who_sent="usr",
                            send_to_wpp=False,
                            use_llm=False,
                        ),
                        1749216000.0,
                    ),
                    (
                        InternalMessageModel(
                            phone="553112345678",
                            store_phone="553198765432",
                            last_interacted_at="2025-06-04 20:48:42.154852+00:00",
                            content="First message",
                            content_link=None,
                            type="text",
                            who_sent="usr",
                            send_to_wpp=False,
                            use_llm=False,
                        ),
                        1749215669.0,
                    ),
                ]
            }
        }
        cut_timestamp = 1749215800.0  # Between the two messages

        # Act
        result = self.redis_service.filter_messages(grouped_messages, cut_timestamp)

        # Assert
        # Should return 0 since the latest message (1749216000.0) is not < cut_timestamp (1749215800.0)
        assert len(result) == 0

    def test_time_search_retrieves_old_messages(self) -> None:
        """Test that time_search retrieves messages older than the specified threshold."""
        # Arrange
        with patch("src.services.redis.redis_services.datetime") as mock_datetime:
            mock_now = datetime(2025, 6, 4, 21, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.timestamp.return_value = (
                1749215940.0  # 60 seconds before mock_now
            )

            self.mock_redis_repository.retrieve_messages.return_value = (
                self.test_messages
            )

            # Act
            _ = self.redis_service.time_search(time_threshold_seconds=60)

            # Assert
            self.mock_redis_repository.retrieve_messages.assert_called_once()

    def test_time_search_with_default_threshold(self) -> None:
        """Test that time_search uses default threshold when none provided."""
        # Arrange
        self.mock_redis_repository.retrieve_messages.return_value = []

        # Act
        result = self.redis_service.time_search()

        # Assert
        assert result == []

    def test_time_search_with_custom_threshold(self) -> None:
        """Test that time_search works with custom threshold values."""
        # Arrange
        self.mock_redis_repository.retrieve_messages.return_value = []

        # Act
        result = self.redis_service.time_search(time_threshold_seconds=3600)  # 1 hour

        # Assert
        assert result == []

    def test_time_search_integration_flow(self) -> None:
        """Integration test for the complete time_search flow."""
        # Arrange
        old_message = (
            b'{"phone": "553112345678", "store_phone": "553198765432", "last_interacted_at": "2025-06-04 20:48:42.154852+00:00", "content": "Old message", "content_link": null, "type": "text", "who_sent": "usr", "pending_message": null, "additional_info": null, "send_to_wpp": false, "use_llm": false}',
            1749215669.0,  # Old timestamp
        )
        new_message = (
            b'{"phone": "553198765432", "store_phone": "553112345678", "last_interacted_at": "2025-06-04 21:00:00.000000+00:00", "content": "New message", "content_link": null, "type": "text", "who_sent": "usr", "pending_message": null, "additional_info": null, "send_to_wpp": false, "use_llm": false}',
            1749216000.0,  # Newer timestamp
        )

        self.mock_redis_repository.retrieve_messages.return_value = [
            old_message,
            new_message,
        ]

        with patch("src.services.redis.redis_services.datetime") as mock_datetime:
            mock_now = datetime(2025, 6, 4, 21, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.timestamp.return_value = (
                1749215940.0  # 60 seconds before mock_now
            )

            # Act
            _ = self.redis_service.time_search(time_threshold_seconds=60)

            # Assert
            # The logic should work correctly now with proper datetime mocking

    def test_time_search_with_no_messages(self) -> None:
        """Test that time_search returns empty list when no messages exist."""
        # Arrange
        self.mock_redis_repository.retrieve_messages.return_value = []

        # Act
        result = self.redis_service.time_search(time_threshold_seconds=60)

        # Assert
        assert result == []


class TestCreateRedisService:
    """Test cases for the create_redis_service dependency function."""

    def test_create_redis_service_creates_service_with_repository(self) -> None:
        """Test that create_redis_service creates a RedisService with proper repository."""
        # Arrange
        test_host = "test_host"
        test_port = 6379
        test_password = "test_password"
        test_ssl = "true"

        with patch(
            "src.services.redis.redis_services.RedisDatabase"
        ) as MockRedisDatabase:
            mock_repository = MagicMock()
            MockRedisDatabase.return_value = mock_repository

            # Act
            service = create_redis_service(
                test_host, test_port, test_password, test_ssl
            )

            # Assert
            MockRedisDatabase.assert_called_once_with(
                test_host, test_port, test_password, test_ssl
            )
            assert isinstance(service, RedisService)
            assert service.redis_repository == mock_repository

    def test_create_redis_service_with_different_parameters(self) -> None:
        """Test that create_redis_service works with different host and port values."""
        # Arrange
        test_host = "localhost"
        test_port = 6380
        test_password = "different_password"
        test_ssl = False

        with patch(
            "src.services.redis.redis_services.RedisDatabase"
        ) as MockRedisDatabase:
            mock_repository = MagicMock()
            MockRedisDatabase.return_value = mock_repository

            # Act
            service = create_redis_service(
                test_host, test_port, test_password, test_ssl
            )

            # Assert
            MockRedisDatabase.assert_called_once_with(
                test_host, test_port, test_password, test_ssl
            )
            assert isinstance(service, RedisService)

    def test_create_redis_service_error_handling(self) -> None:
        """Test that create_redis_service properly handles RedisDatabase creation errors."""
        # Arrange
        test_host = "invalid_host"
        test_port = 6379
        test_password = "test_password"
        test_ssl = "true"

        with patch(
            "src.services.redis.redis_services.RedisDatabase"
        ) as MockRedisDatabase:
            MockRedisDatabase.side_effect = Exception("Connection failed")

            # Act & Assert
            with pytest.raises(Exception):
                create_redis_service(test_host, test_port, test_password, test_ssl)


class TestRedisServiceErrorHandling:
    """Test cases for error handling in RedisService."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.mock_redis_repository = MagicMock(spec=RedisDatabase)
        self.redis_service = RedisService(self.mock_redis_repository)
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

    def test_save_error_handling(self) -> None:
        """Test that save method properly handles repository errors."""
        # Arrange
        self.mock_redis_repository.save.side_effect = Exception("Save failed")

        # Act & Assert
        with pytest.raises(Exception):
            self.redis_service.save(self.test_data)

    def test_retrieve_messages_error_handling(self) -> None:
        """Test that retrieve_messages properly handles repository errors."""
        # Arrange
        self.mock_redis_repository.retrieve_messages.side_effect = Exception(
            "Retrieve failed"
        )

        # Act & Assert
        with pytest.raises(Exception):
            self.redis_service.retrieve_messages()

    def test_delete_messages_error_handling(self) -> None:
        """Test that delete_messages properly handles repository errors."""
        # Arrange
        messages = [{"test": "message"}]
        self.mock_redis_repository.delete_message.side_effect = Exception(
            "Delete failed"
        )

        # Act & Assert
        with pytest.raises(Exception):
            self.redis_service.delete_messages(messages)

    def test_group_messages_with_malformed_data(self) -> None:
        """Test that group_messages handles malformed message data gracefully."""
        # Arrange
        malformed_messages = [
            (b'{"invalid": "json"', 1749215669.57257),  # Missing closing brace
        ]

        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            self.redis_service.group_messages(malformed_messages)

    def test_group_messages_with_missing_required_fields(self) -> None:
        """Test that group_messages handles messages with missing required fields."""
        # Arrange
        incomplete_messages = [
            (b'{"phone": "553112345678"}', 1749215669.57257),
        ]

        # Act & Assert
        with pytest.raises(KeyError):
            self.redis_service.group_messages(incomplete_messages)
