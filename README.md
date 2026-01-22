# Synapse

[![CI](https://github.com/IzzyFuller/synapse/actions/workflows/ci.yml/badge.svg)](https://github.com/IzzyFuller/synapse/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/IzzyFuller/synapse/graph/badge.svg)](https://codecov.io/gh/IzzyFuller/synapse)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Stack-agnostic pub-sub protocols, consumers, and base models for microservices.

## Overview

This library provides:

- **Synchronous Protocols**: `PubSubPublisher`, `PubSubSubscriber`, `MessageHandler`
- **Asynchronous Protocols**: `AsyncPubSubPublisher`, `AsyncPubSubSubscriber`, `AsyncMessageHandler`
- **Consumers**: `MessageConsumer` (sync) and `AsyncMessageConsumer` (async) for pull-based message processing
- **Base Models**: `CamelCaseModel`, `ErrorInfo`, `ErrorDetails` for standardized messaging
- **Request Types**: `PullRequest`, `AcknowledgeRequest` TypedDict definitions for subscriber operations

## Installation

```bash
# Via uv (recommended)
uv add git+https://github.com/IzzyFuller/synapse.git@v0.1.0

# Via pip
pip install git+https://github.com/IzzyFuller/synapse.git@v0.1.0
```

## Usage

### How Protocols Work

This library uses **Python Protocols** (structural subtyping / duck typing). Any client that has the right method signatures automatically implements the protocol - no explicit inheritance or wrapper classes required.

**If your client already matches the protocol signature** → use it directly
**If your client's API differs** → write a thin adapter to conform

### Publisher Protocol

The `PubSubPublisher` protocol requires:
```python
def publish(self, topic: str, data: bytes, **kwargs) -> Any
```

If your pub/sub client already has this signature, it implements the protocol automatically:
```python
# Any client with a matching publish() method works
consumer = MessageConsumer(
    subscription="my-subscription",
    handler=my_handler,
    request_model=MyMessage,
    subscriber=my_subscriber,
    publisher=my_publisher  # Just pass it in
)
```

If your client's API differs, write a thin adapter:
```python
class MyPublisherAdapter:
    """Adapter for a client with a different API."""

    def __init__(self, client):
        self._client = client

    def publish(self, topic: str, data: bytes, **kwargs) -> str:
        # Translate to your client's API
        return self._client.send_message(topic, data)
```

### Subscriber Protocol

The `PubSubSubscriber` protocol requires:
```python
def pull(self, request: PullRequest, timeout: float) -> Any
def acknowledge(self, request: AcknowledgeRequest) -> None
```

Where `PullRequest` and `AcknowledgeRequest` are TypedDict types (compatible with plain dicts):
```python
class PullRequest(TypedDict):
    subscription: str
    max_messages: int

class AcknowledgeRequest(TypedDict):
    subscription: str
    ack_ids: list[str]
```

**Google Cloud Pub/Sub** - The `pubsub_v1.SubscriberClient` already matches this signature and can be used directly:
```python
from google.cloud import pubsub_v1

# GCP client works directly - no adapter needed!
subscriber = pubsub_v1.SubscriberClient()
consumer = MessageConsumer(
    subscription="projects/my-project/subscriptions/my-sub",
    handler=my_handler,
    request_model=MyMessage,
    subscriber=subscriber,  # Pass GCP client directly
)
```

**Other clients** - If your client's API differs, write a thin adapter:
```python
class MySubscriberAdapter:
    """Adapter for a client with a different API."""

    def __init__(self, client):
        self._client = client

    def pull(self, request: PullRequest, timeout: float) -> Any:
        # Access TypedDict values via dict syntax
        return self._client.receive(
            subscription=request["subscription"],
            max_messages=request["max_messages"],
            timeout=timeout
        )

    def acknowledge(self, request: AcknowledgeRequest) -> None:
        self._client.ack(request["subscription"], request["ack_ids"])
```

### Using the Synchronous MessageConsumer

```python
from synapse.consumer import MessageConsumer
from pydantic import BaseModel

class MyMessage(BaseModel):
    """Your message schema."""
    user_id: str
    action: str

class MyHandler:
    """Handler for processing messages."""

    def handle(self, message: MyMessage) -> None:
        # Process message
        print(f"Processing: {message.user_id} - {message.action}")

def main():
    # Set up consumer
    subscriber = GooglePubSubSubscriber(...)
    handler = MyHandler()
    consumer = MessageConsumer(
        subscription="my-subscription",
        handler=handler,
        request_model=MyMessage,
        subscriber=subscriber
    )

    # Start and run consumer
    consumer.start()
    consumer.run()

if __name__ == "__main__":
    main()
```

### Using the Asynchronous MessageConsumer

```python
import asyncio
from synapse.consumer import AsyncMessageConsumer
from pydantic import BaseModel

class MyMessage(BaseModel):
    """Your message schema."""
    user_id: str
    action: str

class MyHandler:
    """Handler for processing messages."""

    async def handle(self, message: MyMessage) -> None:
        # Process message
        print(f"Processing: {message.user_id} - {message.action}")

async def main():
    # Set up consumer
    subscriber = GooglePubSubSubscriber(...)
    handler = MyHandler()
    consumer = AsyncMessageConsumer(
        subscription="my-subscription",
        handler=handler,
        request_model=MyMessage,
        subscriber=subscriber
    )

    # Start and run consumer
    consumer.start()
    await consumer.run()

asyncio.run(main())
```

## Design Philosophy

- **Stack-agnostic**: No cloud provider dependencies; adapters injected by services
- **Protocol-based**: Uses Python Protocols for structural subtyping (duck typing)
- **GCP-compatible**: Subscriber protocols designed to match GCP client signatures directly
- **Minimal dependencies**: Only Pydantic (for error/base models) + stdlib TypedDict
- **Sync and Async**: Both synchronous and asynchronous interfaces for flexibility
- **Type-safe**: TypedDict for request types, Pydantic for message validation

## Development

```bash
# Install dependencies
uv sync --all-groups

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=synapse

# Format and lint code
uv run ruff format src tests
uv run ruff check --fix src tests

# Type check
uv run mypy src
```
