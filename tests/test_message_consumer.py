"""Tests for MessageConsumer."""

import json
from unittest.mock import Mock

import pytest
from pydantic import BaseModel

from synapse.consumer.message_consumer import MessageConsumer


class TestRequest(BaseModel):
    """Test request model for validation."""

    request_id: str
    data: str


class TestMessageConsumer:
    """Test MessageConsumer class."""

    @pytest.fixture
    def mock_subscriber(self):
        """Create a mock subscriber."""
        subscriber = Mock()
        return subscriber

    @pytest.fixture
    def mock_handler(self):
        """Create a mock handler."""
        handler = Mock()
        return handler

    @pytest.fixture
    def consumer(self, mock_subscriber, mock_handler):
        """Create a MessageConsumer instance."""
        return MessageConsumer(
            subscription="projects/test/subscriptions/sync-sub",
            handler=mock_handler,
            request_model=TestRequest,
            subscriber=mock_subscriber,
        )

    def test_consumer_initialization(self, consumer, mock_handler, mock_subscriber):
        """Consumer should initialize with provided dependencies."""
        assert consumer.subscription == "projects/test/subscriptions/sync-sub"
        assert consumer.handler is mock_handler
        assert consumer.request_model is TestRequest
        assert consumer.subscriber is mock_subscriber
        assert consumer._running is False

    def test_start_sets_running_flag(self, consumer):
        """start() should set _running flag to True."""
        consumer.start()
        assert consumer._running is True

    def test_stop_clears_running_flag(self, consumer):
        """stop() should set _running flag to False."""
        consumer.start()
        consumer.stop()
        assert consumer._running is False

    def test_consumer_pulls_from_subscription(self, consumer, mock_subscriber):
        """Consumer should pull messages with correct request dict."""

        # Setup: one message then stop
        def side_effect(*args, **kwargs):
            consumer.stop()
            return Mock(received_messages=[])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        consumer.run()

        # Verify pull was called with correct request dict
        mock_subscriber.pull.assert_called_once()
        call_args = mock_subscriber.pull.call_args
        pull_request = call_args[1]["request"]
        assert pull_request == {
            "subscription": "projects/test/subscriptions/sync-sub",
            "max_messages": 1,
        }
        assert call_args[1]["timeout"] == 30

    def test_consumer_continues_when_no_messages(self, consumer, mock_subscriber, mock_handler):
        """Consumer should continue looping when no messages available."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                consumer.stop()
            return Mock(received_messages=[])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        consumer.run()

        # Should have pulled multiple times
        assert call_count >= 2
        # Handler should never be called
        mock_handler.handle.assert_not_called()

    def test_consumer_parses_and_validates_json(self, consumer, mock_subscriber, mock_handler):
        """Consumer should parse JSON and validate with Pydantic model."""
        # Setup: message with valid JSON
        message_data = {"request_id": "req-123", "data": "test-data"}
        mock_message = Mock()
        mock_message.message.data = json.dumps(message_data).encode("utf-8")
        mock_message.ack_id = "ack-123"

        def side_effect(*args, **kwargs):
            consumer.stop()
            return Mock(received_messages=[mock_message])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        consumer.run()

        # Verify handler was called with validated Pydantic model
        mock_handler.handle.assert_called_once()
        request = mock_handler.handle.call_args[0][0]
        assert isinstance(request, TestRequest)
        assert request.request_id == "req-123"
        assert request.data == "test-data"

    def test_consumer_acknowledges_after_handling(self, consumer, mock_subscriber, mock_handler):
        """Consumer should acknowledge message after handler completes."""
        # Setup
        message_data = {"request_id": "req-456", "data": "test"}
        mock_message = Mock()
        mock_message.message.data = json.dumps(message_data).encode("utf-8")
        mock_message.ack_id = "ack-456"

        def side_effect(*args, **kwargs):
            consumer.stop()
            return Mock(received_messages=[mock_message])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        consumer.run()

        # Verify acknowledge was called with correct request dict
        mock_subscriber.acknowledge.assert_called_once()
        call_args = mock_subscriber.acknowledge.call_args
        ack_request = call_args[1]["request"]
        assert ack_request == {
            "subscription": "projects/test/subscriptions/sync-sub",
            "ack_ids": ["ack-456"],
        }

    def test_consumer_raises_validation_error_for_invalid_data(self, consumer, mock_subscriber):
        """Consumer should raise ValidationError for invalid message data."""
        # Setup: message with invalid JSON (missing required fields)
        invalid_data = {"request_id": "req-789"}  # missing 'data' field
        mock_message = Mock()
        mock_message.message.data = json.dumps(invalid_data).encode("utf-8")
        mock_message.ack_id = "ack-789"

        def side_effect(*args, **kwargs):
            consumer.stop()
            return Mock(received_messages=[mock_message])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        # Should raise validation error
        with pytest.raises(Exception):  # Pydantic ValidationError
            consumer.run()

    def test_consumer_raises_json_decode_error_for_malformed_json(self, consumer, mock_subscriber):
        """Consumer should raise JSONDecodeError for malformed JSON."""
        # Setup: message with malformed JSON
        mock_message = Mock()
        mock_message.message.data = b"{invalid json"
        mock_message.ack_id = "ack-bad"

        def side_effect(*args, **kwargs):
            consumer.stop()
            return Mock(received_messages=[mock_message])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        # Should raise JSON decode error
        with pytest.raises(json.JSONDecodeError):
            consumer.run()

    def test_consumer_processes_message_with_unicode_data(
        self, consumer, mock_subscriber, mock_handler
    ):
        """Consumer should handle Unicode characters in message data."""
        # Setup: message with Unicode
        message_data = {"request_id": "unicode", "data": "测试 ⚡"}
        mock_message = Mock()
        mock_message.message.data = json.dumps(message_data).encode("utf-8")
        mock_message.ack_id = "ack-unicode"

        def side_effect(*args, **kwargs):
            consumer.stop()
            return Mock(received_messages=[mock_message])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        consumer.run()

        # Verify handler received Unicode data correctly
        request = mock_handler.handle.call_args[0][0]
        assert request.data == "测试 ⚡"

    def test_run_processes_messages_in_loop(self, consumer, mock_subscriber, mock_handler):
        """run() should continuously process messages while _running is True."""
        # Setup: Three messages, then stop
        message_data_1 = {"request_id": "req-1", "data": "data-1"}
        message_data_2 = {"request_id": "req-2", "data": "data-2"}
        message_data_3 = {"request_id": "req-3", "data": "data-3"}

        mock_message_1 = Mock()
        mock_message_1.message.data = json.dumps(message_data_1).encode("utf-8")
        mock_message_1.ack_id = "ack-1"

        mock_message_2 = Mock()
        mock_message_2.message.data = json.dumps(message_data_2).encode("utf-8")
        mock_message_2.ack_id = "ack-2"

        mock_message_3 = Mock()
        mock_message_3.message.data = json.dumps(message_data_3).encode("utf-8")
        mock_message_3.ack_id = "ack-3"

        # Return messages, then stop consumer after 3 iterations
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Mock(received_messages=[mock_message_1])
            elif call_count == 2:
                return Mock(received_messages=[mock_message_2])
            elif call_count == 3:
                consumer.stop()
                return Mock(received_messages=[mock_message_3])
            return Mock(received_messages=[])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        consumer.run()

        # Verify handler was called for all 3 messages
        assert mock_handler.handle.call_count == 3

    def test_run_stops_when_stop_called(self, consumer, mock_subscriber):
        """run() should exit when stop() is called."""
        # Setup: No messages, consumer should loop until stopped
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                consumer.stop()
            return Mock(received_messages=[])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        consumer.run()

        # Should have called pull at least 3 times before stopping
        assert call_count >= 3

    def test_run_does_nothing_if_not_started(self, consumer, mock_subscriber):
        """run() should not process messages if start() was not called."""
        mock_subscriber.pull.return_value = Mock(received_messages=[])

        consumer.run()

        # Should not have pulled any messages
        mock_subscriber.pull.assert_not_called()
