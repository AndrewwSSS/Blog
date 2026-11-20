import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.core.security import generate_email_verification_token
from app.pubsub.services.mail_service import EmailService
from app.repositories.user_repository import UserRepository
from app.db.session import async_session
from app.db.unit_of_work import UnitOfWork


logger = logging.getLogger(__name__)


class AsyncKafkaConsumer:
    BATCH_SIZE = 50
    POLL_TIMEOUT_MS = 5000

    def __init__(self):
        self.consumer = AIOKafkaConsumer(
            "new-user-registration",
            "new-active-user",
            bootstrap_servers=settings.KAFKA_URL,
            group_id="notification-service-server",
            auto_offset_reset="latest",
            enable_auto_commit=False,
        )
        self.topic_callbacks = {
            "new-user-registration": self._handle_new_user_registration,
            "new-active-user": self._handle_new_active_user,
        }

    async def _handle_message(self, message) -> None:
        callback = self.topic_callbacks.get(message.topic)
        if not callback:
            logger.error(f"Callback for topic: {message.topic} is not registered")
            return
        try:
            await callback(message)
        except Exception:
            logger.exception(
                f"Failed to handle message {message.topic}"
                f"[{message.partition}]@{message.offset}, skipping it"
            )

    async def _process_batch(self, topic_messages: dict) -> None:
        await asyncio.gather(
            *(
                self._handle_message(message)
                for messages in topic_messages.values()
                for message in messages
            )
        )
        if topic_messages:
            await self.consumer.commit()

    async def _handle_new_active_user(self, message) -> None:
        payload = json.loads(message.value.decode("utf-8"))
        user_email = payload["email"]

        async with UnitOfWork(async_session) as uow:
            user_repo = UserRepository(uow.session)
            user = await user_repo.get_by_email(email=user_email)
            if not user:
                logger.warning(f"User with email {user_email} not found")
                return
            if user.welcome_email_sent:
                logger.debug(f"User {user.username} has already got welcome email")
                return

            is_sent = await EmailService(user).send_welcome_email()

            if is_sent:
                await user_repo.update_by_id(record_id=user.id, welcome_email_sent=True)
            else:
                logger.error(f"Failed to send welcome email to user {user.email}")

    async def _handle_new_user_registration(self, message) -> None:
        payload = json.loads(message.value.decode("utf-8"))
        user_id = int(payload["id"])

        async with UnitOfWork(async_session) as uow:
            user_repo = UserRepository(uow.session)
            user = await user_repo.get_by_id(record_id=user_id)
            if not user:
                logger.warning(f"User with id {user_id} not found")
                return
            if user.is_active:
                logger.info(f"User {user.username} is already verified")
                return

            token = generate_email_verification_token(user.email)
            is_sent = await EmailService(user).send_verification_email(
                verification_url=f"{settings.email_verification_url_prefix}{token}"
            )
            if is_sent:
                logger.info(f"User {user.username} got verification email")
            else:
                logger.error(f"Failed to send verification email to user {user.email}")

    async def start_consuming(self) -> None:
        await self.consumer.start()
        try:
            while True:
                topic_messages = await self.consumer.getmany(
                    max_records=self.BATCH_SIZE,
                    timeout_ms=self.POLL_TIMEOUT_MS,
                )
                await self._process_batch(topic_messages)
        finally:
            await self.consumer.stop()
