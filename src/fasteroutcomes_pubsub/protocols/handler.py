"""Message handler protocol definitions."""

from typing import Protocol, Any, runtime_checkable


@runtime_checkable
class MessageHandler(Protocol):
    """
    Synchronous protocol for message handlers.

    Handlers receive validated request objects and are responsible for:
    - Processing the request synchronously
    - Publishing results (via their own result publisher)
    - Handling all errors internally
    """

    def handle(self, request: Any) -> None:
        """
        Process a validated request and publish result synchronously.

        Args:
            request: Validated request object (type depends on handler)

        Note:
            Handler should catch all exceptions and publish error results.
            If handler raises an exception, message will not be acked and
            Pub/Sub will retry it.
        """
        ...


@runtime_checkable
class AsyncMessageHandler(Protocol):
    """
    Async protocol for message handlers.

    Handlers receive validated request objects and are responsible for:
    - Processing the request asynchronously
    - Publishing results (via their own result publisher)
    - Handling all errors internally
    """

    async def handle(self, request: Any) -> None:
        """
        Process a validated request and publish result asynchronously.

        Args:
            request: Validated request object (type depends on handler)

        Note:
            Handler should catch all exceptions and publish error results.
            If handler raises an exception, message will not be acked and
            Pub/Sub will retry it.
        """
        ...
