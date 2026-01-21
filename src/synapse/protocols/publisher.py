"""Publisher protocol definitions."""

from typing import Protocol, Any, runtime_checkable


@runtime_checkable
class PubSubPublisher(Protocol):
    """Synchronous protocol for publishing messages to Pub/Sub topics."""

    def publish(self, topic: str, data: bytes, **kwargs: Any) -> Any:
        """
        Publish a message to a topic synchronously.

        Args:
            topic: Full topic path (e.g., 'projects/PROJECT_ID/topics/TOPIC_NAME')
            data: Message data as bytes
            **kwargs: Additional keyword arguments (e.g., attributes)

        Returns:
            Message ID or result from the publish operation
        """
        ...


@runtime_checkable
class AsyncPubSubPublisher(Protocol):
    """Async protocol for publishing messages to Pub/Sub topics."""

    async def publish(self, topic: str, data: bytes, **kwargs: Any) -> Any:
        """
        Publish a message to a topic asynchronously.

        Args:
            topic: Full topic path (e.g., 'projects/PROJECT_ID/topics/TOPIC_NAME')
            data: Message data as bytes
            **kwargs: Additional keyword arguments (e.g., attributes)

        Returns:
            Future or message ID from the publish operation
        """
        ...
