"""Generic async message consumer for Pub/Sub."""

import json
import logging
from typing import Type

from pydantic import BaseModel

from synapse.protocols.handler import AsyncMessageHandler
from synapse.protocols.subscriber import AsyncPubSubSubscriber

logger = logging.getLogger(__name__)


class AsyncMessageConsumer:
    """
    Generic asynchronous message consumer for Pub/Sub.

    Responsibilities:
    - Pull messages from subscription asynchronously
    - Parse and validate JSON (using Pydantic)
    - Route to async handler
    - Acknowledge messages asynchronously

    The handler is responsible for:
    - Domain processing logic
    - Publishing results
    - Error handling
    """

    def __init__(
        self,
        subscription: str,
        handler: AsyncMessageHandler,
        request_model: Type[BaseModel],
        subscriber: AsyncPubSubSubscriber,
    ):
        """
        Initialize async message consumer.

        Args:
            subscription: Pub/Sub subscription path
            handler: Async message handler implementing AsyncMessageHandler protocol
            request_model: Pydantic model for validating messages
            subscriber: Async subscriber adapter for pulling messages
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

    async def process_one_message(self) -> None:
        """
        Process a single message from the subscription asynchronously.

        This method:
        1. Pulls one message from subscription
        2. Parses and validates JSON
        3. Routes to async handler
        4. Acknowledges the message
        """
        # Pull message from subscription
        response = await self.subscriber.pull(
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
        await self.handler.handle(request)

        # Acknowledge message
        await self.subscriber.acknowledge(
            request={"subscription": self.subscription, "ack_ids": [received_message.ack_id]}
        )

    async def run(self) -> None:
        """
        Run the async message consumer loop.

        Continuously processes messages from the subscription while running.
        Call start() before run(), and stop() to exit the loop.
        """
        while self._running:
            await self.process_one_message()
