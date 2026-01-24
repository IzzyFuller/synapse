"""Fixtures for RabbitMQ integration tests."""

import subprocess
import time

import pika
import pytest

RABBITMQ_PORT = 5673  # Non-default port to avoid conflicts


@pytest.fixture(scope="session")
def rabbitmq_container():
    """Start RabbitMQ Docker container for test session."""
    container_name = "synapse-rabbitmq-test"

    # Clean up any existing container
    subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    # Start RabbitMQ
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            f"{RABBITMQ_PORT}:5672",
            "rabbitmq:3-management",
        ],
        check=True,
        capture_output=True,
    )

    # Wait for RabbitMQ to be ready
    time.sleep(10)

    yield

    # Cleanup
    subprocess.run(["docker", "stop", container_name], capture_output=True)
    subprocess.run(["docker", "rm", container_name], capture_output=True)


@pytest.fixture(scope="session")
def rabbitmq_connection(rabbitmq_container) -> pika.BlockingConnection:
    """Provide RabbitMQ connection."""
    return pika.BlockingConnection(pika.ConnectionParameters(host="localhost", port=RABBITMQ_PORT))


@pytest.fixture
def test_queue(rabbitmq_connection) -> str:
    """Create a unique test queue and clean up after test."""
    import uuid

    queue_name = f"test-queue-{uuid.uuid4()}"
    channel = rabbitmq_connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)

    yield queue_name

    # Cleanup
    channel.queue_delete(queue=queue_name)
