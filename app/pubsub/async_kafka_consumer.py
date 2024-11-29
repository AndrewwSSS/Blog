import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer, TopicPartition

from app.core.config import settings
from app.pubsub.services.mail_service import EmailService
from app.repositories.user_repository import UserRepository
from app.db.session import async_session


logger = logging.getLogger(__name__)


class AsyncKafkaConsumer:
    def __init__(self):
        self.consumer = AIOKafkaConsumer(
            "new-user-registration", "new-active-user",
            bootstrap_servers=settings.KAFKA_URL,
            group_id="notification-service-server",
            auto_offset_reset="latest",
            enable_auto_commit=False,
        )
        self.topic_callbacks = {
            "new-user-registration": self._handle_new_user_registration,
            "new-active-user": self._handle_new_active_user,
        }
        self.BATCH_SIZE = 50
        self.POOL_TIMEOUT = 5000

    async def _handle_message(self, message) -> None:
        topic = message.topic
        if topic not in self.topic_callbacks:
            logger.error(f"Callback for topic: {topic} is not registered")
            return
        await self.topic_callbacks[topic](message)

    async def _commit_message(self, message) -> None:
        tp = TopicPartition(message.topic, message.partition)
        await self.consumer.commit(
            {
                tp: message.offset + 1,
            }
        )

    async def _handle_new_active_user(self, message) -> None:
        value = message.value.decode("utf-8")
        payload = json.loads(value)
        user_email = payload["email"]

        async with async_session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_email(
                email=user_email,
            )
            if user.welcome_email_sent:
                logger.debug(f"User {user.username} has already got welcome email")
                await self._commit_message(message)
                return

            email_service = EmailService(user)
            is_sent = await email_service.send_welcome_email()

            if is_sent:
                await user_repo.update_by_id(
                    user.id,
                    {"welcome_email_sent": True}
                )
            else:
                logger.error(f"Failed to send welcome email to user {user.email}")
            await self._commit_message(message)

    async def _handle_new_user_registration(self, message) -> None:
        value = message.value.decode("utf-8")
        payload = json.loads(value)
        user_id = int(payload["id"])
        verification_url = payload["verification_url"]

        async with async_session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(
                user_id=user_id,
            )
            if user.is_active:
                logger.info(f"User {user.username} has already registered")
                return
            service = EmailService(user)
            is_sent = await service.send_verification_email(
                verification_url=verification_url
            )
            if is_sent:
                logger.info(f"User {user.username} got verification email")
            else:
                logger.error(f"Failed to send verification email to user {user.email}")
        await self._commit_message(message)

    async def start_consuming(self) -> None:
        await self.consumer.start()
        try:
            while True:
                topic_messages = await self.consumer.getmany(
                    max_records=self.BATCH_SIZE,
                    timeout_ms=self.POOL_TIMEOUT
                )
                
                coroutines = []
                for topic, messages in topic_messages.items():
                    coroutines.extend(
                        self._handle_message(message) for message in messages
                    )
                    
                await asyncio.gather(*coroutines)

        finally:
            await self.consumer.stop()
