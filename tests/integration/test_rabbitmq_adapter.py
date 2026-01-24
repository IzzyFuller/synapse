"""Integration tests for RabbitMQ adapter against real RabbitMQ."""

import pytest

from synapse.adapters.rabbitmq import RabbitMQPublisher, RabbitMQSubscriber
from synapse.models.response import PullResponse


@pytest.mark.integration
class TestRabbitMQPublisher:
    """Integration tests for RabbitMQPublisher."""

    def test_publish_sends_message_to_queue(self, rabbitmq_connection, test_queue):
        """Publisher sends message that can be consumed from queue."""
        publisher = RabbitMQPublisher(rabbitmq_connection)

        # Publish message
        result = publisher.publish(topic=test_queue, data=b"hello world")

        # Verify message was published (result has message_id)
        assert result.result() is not None

        # Verify message is in queue by consuming it directly
        channel = rabbitmq_connection.channel()
        method, properties, body = channel.basic_get(queue=test_queue, auto_ack=True)

        assert body == b"hello world"

    def test_publish_with_routing_key(self, rabbitmq_connection):
        """Publisher parses exchange:routing_key format."""
        setup_channel = rabbitmq_connection.channel()

        # Create exchange and queue with binding
        exchange_name = "test-exchange"
        queue_name = "test-routed-queue"
        routing_key = "test.route"

        setup_channel.exchange_declare(exchange=exchange_name, exchange_type="direct")
        setup_channel.queue_declare(queue=queue_name, durable=True)
        setup_channel.queue_bind(queue=queue_name, exchange=exchange_name, routing_key=routing_key)

        try:
            publisher = RabbitMQPublisher(rabbitmq_connection)

            # Publish with exchange:routing_key format
            publisher.publish(topic=f"{exchange_name}:{routing_key}", data=b"routed message")

            # Verify message arrived in queue (use fresh channel)
            verify_channel = rabbitmq_connection.channel()
            method, properties, body = verify_channel.basic_get(queue=queue_name, auto_ack=True)
            assert body == b"routed message"

        finally:
            # Cleanup
            cleanup_channel = rabbitmq_connection.channel()
            cleanup_channel.queue_delete(queue=queue_name)
            cleanup_channel.exchange_delete(exchange=exchange_name)

    def test_publish_binary_data(self, rabbitmq_connection, test_queue):
        """Publisher handles arbitrary binary data."""
        publisher = RabbitMQPublisher(rabbitmq_connection)

        # Binary data with all byte values
        binary_data = bytes(range(256))
        publisher.publish(topic=test_queue, data=binary_data)

        # Verify binary data preserved
        channel = rabbitmq_connection.channel()
        method, properties, body = channel.basic_get(queue=test_queue, auto_ack=True)

        assert body == binary_data


@pytest.mark.integration
class TestRabbitMQSubscriber:
    """Integration tests for RabbitMQSubscriber."""

    def test_pull_receives_message(self, rabbitmq_connection, test_queue):
        """Subscriber pulls message from queue."""
        # Publish a message first
        channel = rabbitmq_connection.channel()
        channel.basic_publish(exchange="", routing_key=test_queue, body=b"test message")

        # Pull with subscriber
        subscriber = RabbitMQSubscriber(rabbitmq_connection)
        response = subscriber.pull(
            request={"subscription": test_queue, "max_messages": 1},
            timeout=5.0,
        )

        assert isinstance(response, PullResponse)
        assert len(response.received_messages) == 1
        assert response.received_messages[0].message.data == b"test message"
        assert response.received_messages[0].ack_id is not None

        # Acknowledge to clean up
        subscriber.acknowledge(
            request={"subscription": test_queue, "ack_ids": [response.received_messages[0].ack_id]}
        )

    def test_pull_returns_empty_on_timeout(self, rabbitmq_connection, test_queue):
        """Subscriber returns empty response when no messages and timeout expires."""
        subscriber = RabbitMQSubscriber(rabbitmq_connection)

        response = subscriber.pull(
            request={"subscription": test_queue, "max_messages": 1},
            timeout=1.0,  # Short timeout
        )

        assert isinstance(response, PullResponse)
        assert len(response.received_messages) == 0

    def test_acknowledge_removes_message(self, rabbitmq_connection, test_queue):
        """Acknowledged messages are removed from queue."""
        # Publish a message
        channel = rabbitmq_connection.channel()
        channel.basic_publish(exchange="", routing_key=test_queue, body=b"ack test")

        subscriber = RabbitMQSubscriber(rabbitmq_connection)

        # Pull and acknowledge
        response = subscriber.pull(
            request={"subscription": test_queue, "max_messages": 1},
            timeout=5.0,
        )
        subscriber.acknowledge(
            request={"subscription": test_queue, "ack_ids": [response.received_messages[0].ack_id]}
        )

        # Try to pull again - should be empty
        response2 = subscriber.pull(
            request={"subscription": test_queue, "max_messages": 1},
            timeout=1.0,
        )

        assert len(response2.received_messages) == 0

    def test_unacknowledged_message_redelivered(self, rabbitmq_connection, test_queue):
        """Unacknowledged messages are redelivered after connection reset."""
        # Publish a message
        channel = rabbitmq_connection.channel()
        channel.basic_publish(exchange="", routing_key=test_queue, body=b"redeliver test")

        # Pull but don't acknowledge - create new subscriber to simulate disconnect
        subscriber1 = RabbitMQSubscriber(rabbitmq_connection)
        response1 = subscriber1.pull(
            request={"subscription": test_queue, "max_messages": 1},
            timeout=5.0,
        )
        assert len(response1.received_messages) == 1

        # Cancel the consumer without acking (simulates disconnect)
        # The channel.cancel() is called internally by pull(), so we need to
        # use basic_nack to explicitly reject
        ack_id = response1.received_messages[0].ack_id
        delivery_tag = subscriber1._pending_acks.get(ack_id)
        if delivery_tag:
            subscriber1._channel.basic_nack(delivery_tag=delivery_tag, requeue=True)

        # New subscriber should see the message again
        subscriber2 = RabbitMQSubscriber(rabbitmq_connection)
        response2 = subscriber2.pull(
            request={"subscription": test_queue, "max_messages": 1},
            timeout=5.0,
        )

        assert len(response2.received_messages) == 1
        assert response2.received_messages[0].message.data == b"redeliver test"

        # Clean up
        subscriber2.acknowledge(
            request={"subscription": test_queue, "ack_ids": [response2.received_messages[0].ack_id]}
        )


@pytest.mark.integration
class TestRabbitMQRoundTrip:
    """Integration tests for publisher + subscriber together."""

    def test_publish_then_consume_roundtrip(self, rabbitmq_connection, test_queue):
        """Full roundtrip: publish, pull, acknowledge."""
        publisher = RabbitMQPublisher(rabbitmq_connection)
        subscriber = RabbitMQSubscriber(rabbitmq_connection)

        # Publish
        message_data = b'{"request_id": "123", "data": "test"}'
        publisher.publish(topic=test_queue, data=message_data)

        # Pull
        response = subscriber.pull(
            request={"subscription": test_queue, "max_messages": 1},
            timeout=5.0,
        )

        assert len(response.received_messages) == 1
        assert response.received_messages[0].message.data == message_data

        # Acknowledge
        subscriber.acknowledge(
            request={"subscription": test_queue, "ack_ids": [response.received_messages[0].ack_id]}
        )

    def test_multiple_messages_roundtrip(self, rabbitmq_connection, test_queue):
        """Multiple messages can be published and consumed in order."""
        publisher = RabbitMQPublisher(rabbitmq_connection)
        subscriber = RabbitMQSubscriber(rabbitmq_connection)

        # Publish 3 messages
        messages = [b"first", b"second", b"third"]
        for msg in messages:
            publisher.publish(topic=test_queue, data=msg)

        # Consume all 3
        received = []
        for _ in range(3):
            response = subscriber.pull(
                request={"subscription": test_queue, "max_messages": 1},
                timeout=5.0,
            )
            if response.received_messages:
                received.append(response.received_messages[0].message.data)
                subscriber.acknowledge(
                    request={
                        "subscription": test_queue,
                        "ack_ids": [response.received_messages[0].ack_id],
                    }
                )

        assert received == messages
