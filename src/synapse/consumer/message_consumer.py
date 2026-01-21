"""Generic synchronous message consumer for Pub/Sub."""

import json
import logging
from typing import Type

from pydantic import BaseModel

from synapse.protocols.handler import MessageHandler
from synapse.protocols.subscriber import PubSubSubscriber

logger = logging.getLogger(__name__)


class MessageConsumer:
    """
    Generic synchronous message consumer for Pub/Sub.

    Responsibilities:
    - Pull messages from subscription synchronously
    - Parse and validate JSON (using Pydantic)
    - Route to handler
    - Acknowledge messages synchronously

    The handler is responsible for:
    - Domain processing logic
    - Publishing results
    - Error handling
    """

    def __init__(
        self,
        subscription: str,
        handler: MessageHandler,
        request_model: Type[BaseModel],
        subscriber: PubSubSubscriber,
    ):
        """
        Initialize synchronous message consumer.

        Args:
            subscription: Pub/Sub subscription path
            handler: Message handler implementing MessageHandler protocol
            request_model: Pydantic model for validating messages
            subscriber: Subscriber adapter for pulling messages
        """
        self.subscription = subscription
        self.handler = handler
        self.request_model = request_model
        self.subscriber = subscriber
        self._running = False

    def start(self) -> None:
        """Start the message consumer."""
        self._running = True

    def stop(self) -> None:
        """Stop the message consumer."""
        self._running = False

    def process_one_message(self) -> None:
        """
        Process a single message from the subscription synchronously.

        This method:
        1. Pulls one message from subscription
        2. Parses and validates JSON
        3. Routes to handler
        4. Acknowledges the message
        """
        # Pull message from subscription
        response = self.subscriber.pull(
            request={"subscription": self.subscription, "max_messages": 1},
            timeout=30,
        )

        if not response.received_messages:
            return  # No messages available

        received_message = response.received_messages[0]
        message_data = json.loads(received_message.message.data)

        # Validate message
        request = self.request_model(**message_data)

        # Route to handler
        self.handler.handle(request)

        # Acknowledge message
        self.subscriber.acknowledge(
            request={"subscription": self.subscription, "ack_ids": [received_message.ack_id]}
        )

    def run(self) -> None:
        """
        Run the synchronous message consumer loop.

        Continuously processes messages from the subscription while running.
        Call start() before run(), and stop() to exit the loop.
        """
        while self._running:
            self.process_one_message()
