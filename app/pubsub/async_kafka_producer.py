from aiokafka import AIOKafkaProducer

from app.core.config import settings


class AsyncKafkaProducer:
    _producer: AIOKafkaProducer | None = None

    class ProducerNotInitialized(Exception): ...

    @classmethod
    async def init(cls):
        if cls._producer:
            return None

        producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_URL,
            retry_backoff_ms=100,
            acks="all",
            enable_idempotence=True,
        )
        try:
            await producer.start()
        except Exception:
            await producer.stop()
            raise
        cls._producer = producer

    @classmethod
    async def stop(cls):
        if not cls._producer:
            return None

        await cls._producer.stop()
        cls._producer = None

    @classmethod
    async def publish(
        cls,
        topic: str,
        data: str,
        key: str | None = None,
    ) -> None:
        if key:
            key = key.encode("utf-8")

        if not cls._producer:
            raise cls.ProducerNotInitialized()

        await cls._producer.send_and_wait(
            topic=topic,
            key=key,
            value=data.encode("utf-8"),
        )
