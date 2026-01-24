"""RabbitMQ publisher implementing PubSubPublisher protocol."""

from typing import Any

import pika
from pika.adapters.blocking_connection import BlockingChannel

from synapse.models.response import PublishFuture


class RabbitMQPublisher:
    """
    RabbitMQ publisher implementing PubSubPublisher protocol.

    Topic format: "queue_name" or "exchange_name:routing_key"
    If no routing key provided, publishes directly to queue (default exchange).
    """

    def __init__(self, connection: pika.BlockingConnection):
        self._connection = connection
        self._channel: BlockingChannel = connection.channel()

    def publish(self, topic: str, data: bytes, **_kwargs: Any) -> PublishFuture:
        """
        Publish a message to a RabbitMQ queue or exchange.

        Args:
            topic: Queue name, or "exchange:routing_key" format
            data: Message data as bytes
            **kwargs: Additional arguments (ignored for RabbitMQ)

        Returns:
            PublishFuture with message ID
        """
        # Parse topic as "exchange:routing_key" or just "queue_name"
        if ":" in topic:
            exchange, routing_key = topic.split(":", 1)
        else:
            exchange = ""
            routing_key = topic

        self._channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=data,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent
            ),
        )

        # RabbitMQ doesn't return message IDs for basic_publish
        # Return empty string for protocol compatibility
        return PublishFuture(message_id="")
