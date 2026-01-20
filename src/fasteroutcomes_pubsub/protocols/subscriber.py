"""Subscriber protocol definitions."""

from typing import Protocol, Any, runtime_checkable

from fasteroutcomes_pubsub.models.request import PullRequest, AcknowledgeRequest


@runtime_checkable
class PubSubSubscriber(Protocol):
    """Synchronous protocol for subscribing to and consuming Pub/Sub messages."""

    def pull(self, request: PullRequest, timeout: float) -> Any:
        """
        Pull messages from a subscription synchronously.

        Args:
            request: Pull request with subscription path and max_messages
            timeout: Timeout in seconds

        Returns:
            Pull response with received_messages
        """
        ...

    def acknowledge(self, request: AcknowledgeRequest) -> None:
        """
        Acknowledge messages synchronously.

        Args:
            request: Acknowledge request with subscription path and ack_ids
        """
        ...


@runtime_checkable
class AsyncPubSubSubscriber(Protocol):
    """Async protocol for subscribing to and consuming Pub/Sub messages."""

    async def pull(self, request: PullRequest, timeout: float) -> Any:
        """
        Pull messages from a subscription asynchronously.

        Args:
            request: Pull request with subscription path and max_messages
            timeout: Timeout in seconds

        Returns:
            Pull response with received_messages
        """
        ...

    async def acknowledge(self, request: AcknowledgeRequest) -> None:
        """
        Acknowledge messages asynchronously.

        Args:
            request: Acknowledge request with subscription path and ack_ids
        """
        ...
