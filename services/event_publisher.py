import os
import json
from typing import Any, Dict

import aio_pika


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
EVENTS_EXCHANGE = os.getenv("EVENTS_EXCHANGE", "events")


async def publish_event(routing_key: str, payload: Dict[str, Any]) -> None:
    """Publish an event to a topic exchange.

    This is a simple, per-call connect/publish helper suitable for low volume
    or demo usage. For higher throughput, reuse the connection and channel.
    """
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(EVENTS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
        message = aio_pika.Message(
            body=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await exchange.publish(message, routing_key=routing_key)


