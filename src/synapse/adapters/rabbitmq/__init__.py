"""RabbitMQ adapter for synapse pub-sub protocols."""

from synapse.adapters.rabbitmq.publisher import RabbitMQPublisher
from synapse.adapters.rabbitmq.subscriber import RabbitMQSubscriber

__all__ = ["RabbitMQPublisher", "RabbitMQSubscriber"]
