import asyncio
from app.pubsub.async_kafka_consumer import AsyncKafkaConsumer


async def main() -> None:
    listener = AsyncKafkaConsumer()
    await listener.start_consuming()

if __name__ == "__main__":
    asyncio.run(main())
