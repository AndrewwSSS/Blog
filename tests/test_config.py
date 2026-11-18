import json
from pathlib import Path

import pytest

from app.core.config import Settings, settings
from app.pubsub.async_kafka_producer import AsyncKafkaProducer
from app.schemas.user import UserInDB, UserRegister
from app.services.user_service import UserService

ENV_TEMPLATE = Path(__file__).resolve().parent.parent / ".env.template"

REQUIRED = {
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "password",
    "POSTGRES_DB": "blog",
    "POSTGRES_HOST": "db",
    "SECRET_KEY": "secret",
    "EMAIL_TOKEN_SALT": "salt",
    "KAFKA_URL": "kafka:9092",
    "SMTP_USER": "smtp-user",
    "SMTP_USER_PASSWORD": "smtp-password",
}
OPTIONAL_WITH_DEFAULTS = {
    "POSTGRES_PORT": 5432,
    "REDIS_PORT": 6379,
    "ACCESS_TOKEN_EXPIRE_MINUTES": 30,
    "EMAIL_TOKEN_EXPIRE_HOURS": 24,
}


@pytest.fixture
def required_env(monkeypatch) -> None:
    for name, value in REQUIRED.items():
        monkeypatch.setenv(name, value)
    for name in OPTIONAL_WITH_DEFAULTS:
        monkeypatch.delenv(name, raising=False)


def test_env_template_with_empty_optional_values_loads(required_env):
    loaded = Settings(_env_file=ENV_TEMPLATE)

    for name, default in OPTIONAL_WITH_DEFAULTS.items():
        assert getattr(loaded, name) == default


def test_database_url_uses_configured_port(required_env):
    loaded = Settings(_env_file=None, POSTGRES_PORT=6543)

    assert loaded.database_url == "postgresql+asyncpg://user:password@db:6543/blog"


class FakeUserRepository:
    async def create(self, **data) -> UserInDB:
        return UserInDB(
            id=1,
            username=data["username"],
            email=data["email"],
            hashed_password=data["hashed_password"],
            post_auto_reply=False,
            reply_after=1.0,
            welcome_email_sent=False,
            is_active=False,
            is_admin=False,
        )


async def test_verification_link_uses_public_base_url(monkeypatch):
    published = []

    async def fake_publish(topic: str, data: str, key: str | None = None) -> None:
        published.append((topic, json.loads(data)))

    monkeypatch.setattr(AsyncKafkaProducer, "publish", fake_publish)
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "https://blog.example.com/")

    await UserService(FakeUserRepository()).create(
        UserRegister(username="alice", email="alice@example.com", password="pw")
    )

    [(topic, payload)] = published
    assert topic == "new-user-registration"
    assert payload["verification_url"].startswith(
        "https://blog.example.com/api/v1/users/verification/"
    )
