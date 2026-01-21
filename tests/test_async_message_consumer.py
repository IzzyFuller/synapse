"""Tests for AsyncMessageConsumer."""

import json
from unittest.mock import Mock, AsyncMock

import pytest
from pydantic import BaseModel

from synapse.consumer.async_message_consumer import AsyncMessageConsumer


class AsyncTestRequest(BaseModel):
    """Test request model for validation."""

    request_id: str
    data: str


class TestAsyncMessageConsumer:
    """Test AsyncMessageConsumer class."""

    @pytest.fixture
    def mock_subscriber(self):
        """Create a mock async subscriber."""
        subscriber = AsyncMock()
        return subscriber

    @pytest.fixture
    def mock_handler(self):
        """Create a mock async handler."""
        handler = AsyncMock()
        return handler

    @pytest.fixture
    def consumer(self, mock_subscriber, mock_handler):
        """Create an AsyncMessageConsumer instance."""
        return AsyncMessageConsumer(
            subscription="projects/test/subscriptions/async-sub",
            handler=mock_handler,
            request_model=AsyncTestRequest,
            subscriber=mock_subscriber,
        )

    def test_consumer_initialization(self, consumer, mock_handler, mock_subscriber):
        """Consumer should initialize with provided dependencies."""
        assert consumer.subscription == "projects/test/subscriptions/async-sub"
        assert consumer.handler is mock_handler
        assert consumer.request_model is AsyncTestRequest
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

    @pytest.mark.asyncio
    async def test_consumer_pulls_from_subscription(self, consumer, mock_subscriber):
        """Consumer should pull messages with correct request dict."""

        # Setup: one message then stop
        async def side_effect(*args, **kwargs):
            consumer.stop()
            return Mock(received_messages=[])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        await consumer.run()

        # Verify pull was called with correct request dict
        mock_subscriber.pull.assert_called_once()
        call_args = mock_subscriber.pull.call_args
        pull_request = call_args[1]["request"]
        assert pull_request == {
            "subscription": "projects/test/subscriptions/async-sub",
            "max_messages": 1,
        }
        assert call_args[1]["timeout"] == 30

    @pytest.mark.asyncio
    async def test_consumer_continues_when_no_messages(
        self, consumer, mock_subscriber, mock_handler
    ):
        """Consumer should continue looping when no messages available."""
        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                consumer.stop()
            return Mock(received_messages=[])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        await consumer.run()

        # Should have pulled multiple times
        assert call_count >= 2
        # Handler should never be called
        mock_handler.handle.assert_not_called()

    @pytest.mark.asyncio
    async def test_consumer_parses_and_validates_json(
        self, consumer, mock_subscriber, mock_handler
    ):
        """Consumer should parse JSON and validate with Pydantic model."""
        # Setup: message with valid JSON
        message_data = {"request_id": "async-req-123", "data": "async-test-data"}
        mock_message = Mock()
        mock_message.message.data = json.dumps(message_data).encode("utf-8")
        mock_message.ack_id = "async-ack-123"

        async def side_effect(*args, **kwargs):
            consumer.stop()
            return Mock(received_messages=[mock_message])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        await consumer.run()

        # Verify handler was called with validated Pydantic model
        mock_handler.handle.assert_called_once()
        request = mock_handler.handle.call_args[0][0]
        assert isinstance(request, AsyncTestRequest)
        assert request.request_id == "async-req-123"
        assert request.data == "async-test-data"

    @pytest.mark.asyncio
    async def test_consumer_acknowledges_after_handling(
        self, consumer, mock_subscriber, mock_handler
    ):
        """Consumer should acknowledge message after handler completes."""
        # Setup
        message_data = {"request_id": "async-req-456", "data": "async-test"}
        mock_message = Mock()
        mock_message.message.data = json.dumps(message_data).encode("utf-8")
        mock_message.ack_id = "async-ack-456"

        async def side_effect(*args, **kwargs):
            consumer.stop()
            return Mock(received_messages=[mock_message])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        await consumer.run()

        # Verify acknowledge was called with correct request dict
        mock_subscriber.acknowledge.assert_called_once()
        call_args = mock_subscriber.acknowledge.call_args
        ack_request = call_args[1]["request"]
        assert ack_request == {
            "subscription": "projects/test/subscriptions/async-sub",
            "ack_ids": ["async-ack-456"],
        }

    @pytest.mark.asyncio
    async def test_consumer_raises_validation_error_for_invalid_data(
        self, consumer, mock_subscriber
    ):
        """Consumer should raise ValidationError for invalid message data."""
        # Setup: message with invalid JSON (missing required fields)
        invalid_data = {"request_id": "async-req-789"}  # missing 'data' field
        mock_message = Mock()
        mock_message.message.data = json.dumps(invalid_data).encode("utf-8")
        mock_message.ack_id = "async-ack-789"

        async def side_effect(*args, **kwargs):
            consumer.stop()
            return Mock(received_messages=[mock_message])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        # Should raise validation error
        with pytest.raises(Exception):  # Pydantic ValidationError
            await consumer.run()

    @pytest.mark.asyncio
    async def test_consumer_raises_json_decode_error_for_malformed_json(
        self, consumer, mock_subscriber
    ):
        """Consumer should raise JSONDecodeError for malformed JSON."""
        # Setup: message with malformed JSON
        mock_message = Mock()
        mock_message.message.data = b"{invalid json async"
        mock_message.ack_id = "async-ack-bad"

        async def side_effect(*args, **kwargs):
            consumer.stop()
            return Mock(received_messages=[mock_message])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        # Should raise JSON decode error
        with pytest.raises(json.JSONDecodeError):
            await consumer.run()

    @pytest.mark.asyncio
    async def test_consumer_processes_message_with_unicode_data(
        self, consumer, mock_subscriber, mock_handler
    ):
        """Consumer should handle Unicode characters in message data."""
        # Setup: message with Unicode
        message_data = {"request_id": "async-unicode", "data": "异步测试 ⚡"}
        mock_message = Mock()
        mock_message.message.data = json.dumps(message_data).encode("utf-8")
        mock_message.ack_id = "async-ack-unicode"

        async def side_effect(*args, **kwargs):
            consumer.stop()
            return Mock(received_messages=[mock_message])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        await consumer.run()

        # Verify handler received Unicode data correctly
        request = mock_handler.handle.call_args[0][0]
        assert request.data == "异步测试 ⚡"

    @pytest.mark.asyncio
    async def test_run_processes_messages_in_loop(self, consumer, mock_subscriber, mock_handler):
        """run() should continuously process messages while _running is True."""
        # Setup: Three messages, then stop
        message_data_1 = {"request_id": "async-req-1", "data": "async-data-1"}
        message_data_2 = {"request_id": "async-req-2", "data": "async-data-2"}
        message_data_3 = {"request_id": "async-req-3", "data": "async-data-3"}

        mock_message_1 = Mock()
        mock_message_1.message.data = json.dumps(message_data_1).encode("utf-8")
        mock_message_1.ack_id = "async-ack-1"

        mock_message_2 = Mock()
        mock_message_2.message.data = json.dumps(message_data_2).encode("utf-8")
        mock_message_2.ack_id = "async-ack-2"

        mock_message_3 = Mock()
        mock_message_3.message.data = json.dumps(message_data_3).encode("utf-8")
        mock_message_3.ack_id = "async-ack-3"

        # Return messages, then stop consumer after 3 iterations
        call_count = 0

        async def side_effect(*args, **kwargs):
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
        await consumer.run()

        # Verify handler was called for all 3 messages
        assert mock_handler.handle.call_count == 3

    @pytest.mark.asyncio
    async def test_run_stops_when_stop_called(self, consumer, mock_subscriber):
        """run() should exit when stop() is called."""
        # Setup: No messages, consumer should loop until stopped
        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                consumer.stop()
            return Mock(received_messages=[])

        mock_subscriber.pull.side_effect = side_effect

        consumer.start()
        await consumer.run()

        # Should have called pull at least 3 times before stopping
        assert call_count >= 3

    @pytest.mark.asyncio
    async def test_run_does_nothing_if_not_started(self, consumer, mock_subscriber):
        """run() should not process messages if start() was not called."""
        mock_subscriber.pull.return_value = Mock(received_messages=[])

        await consumer.run()

        # Should not have pulled any messages
        mock_subscriber.pull.assert_not_called()
