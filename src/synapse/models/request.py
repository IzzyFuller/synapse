"""Request models for pub-sub operations."""

from typing import TypedDict


class PullRequest(TypedDict):
    """Request for pulling messages from a subscription."""

    subscription: str
    max_messages: int


class AcknowledgeRequest(TypedDict):
    """Request for acknowledging messages."""

    subscription: str
    ack_ids: list[str]
