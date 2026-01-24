"""Response models for pub-sub adapters."""

from dataclasses import dataclass


@dataclass
class Message:
    """Message data container matching GCP Pub/Sub structure."""

    data: bytes


@dataclass
class ReceivedMessage:
    """Received message container matching GCP Pub/Sub structure."""

    message: Message
    ack_id: str


@dataclass
class PullResponse:
    """Pull response container matching GCP Pub/Sub structure."""

    received_messages: list[ReceivedMessage]


@dataclass
class PublishFuture:
    """Future-like object for publish result."""

    message_id: str

    def result(self) -> str:
        """Return the message ID (blocking call for compatibility)."""
        return self.message_id
