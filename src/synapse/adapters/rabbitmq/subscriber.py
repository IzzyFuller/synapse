"""RabbitMQ subscriber implementing PubSubSubscriber protocol."""

import pika
from pika.adapters.blocking_connection import BlockingChannel

from synapse.models.request import PullRequest, AcknowledgeRequest
from synapse.models.response import Message, ReceivedMessage, PullResponse


class RabbitMQSubscriber:
    """
    RabbitMQ subscriber implementing PubSubSubscriber protocol.

    Maps delivery_tag to ack_id for acknowledge() calls.
    """

    def __init__(self, connection: pika.BlockingConnection):
        self._connection = connection
        self._channel: BlockingChannel = connection.channel()
        # Map ack_id (str) -> delivery_tag (int) for acknowledge
        self._pending_acks: dict[str, int] = {}

    def pull(self, request: PullRequest, timeout: float) -> PullResponse:
        """
        Pull one message from a RabbitMQ queue.

        Args:
            request: PullRequest with subscription (queue name)
            timeout: Timeout in seconds (used as inactivity timeout)

        Returns:
            PullResponse with received messages
        """
        queue = request["subscription"]

        received_messages: list[ReceivedMessage] = []

        # Use consume() with inactivity_timeout for proper timeout behavior
        for method, _properties, body in self._channel.consume(
            queue=queue,
            auto_ack=False,
            inactivity_timeout=timeout,
        ):
            if method is None:
                # Timeout reached, no message available
                break

            # Create ack_id from delivery_tag
            ack_id = str(method.delivery_tag)
            self._pending_acks[ack_id] = method.delivery_tag

            received_messages.append(
                ReceivedMessage(
                    message=Message(data=body),
                    ack_id=ack_id,
                )
            )
            break

        # Cancel consumer to allow reuse
        self._channel.cancel()

        return PullResponse(received_messages=received_messages)

    def acknowledge(self, request: AcknowledgeRequest) -> None:
        """
        Acknowledge messages by their ack_ids.

        Args:
            request: AcknowledgeRequest with subscription and ack_ids
        """
        for ack_id in request["ack_ids"]:
            delivery_tag = self._pending_acks.pop(ack_id, None)
            if delivery_tag is not None:
                self._channel.basic_ack(delivery_tag=delivery_tag)
