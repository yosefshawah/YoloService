import os
import json
import asyncio
import aio_pika


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
EVENTS_EXCHANGE = os.getenv("EVENTS_EXCHANGE", "events")


async def handle_message(message: aio_pika.IncomingMessage) -> None:
    async with message.process(requeue=False):
        data = json.loads(message.body.decode("utf-8"))
        print(f"[billing] received: {data}")


async def main() -> None:
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(EVENTS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue("billing.events", durable=True)
        # Subscribe to all image processed events
        await queue.bind(exchange, routing_key="images.processed")
        print(" [*] Billing consumer waiting on 'images.processed'")
        await queue.consume(handle_message)
        await asyncio.Future()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())


