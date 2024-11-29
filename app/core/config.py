from typing import ClassVar
from typing import Type

from pydantic import ConfigDict
from pydantic_settings import BaseSettings

from app.core.reply_generators.base_ai_reply_generator import BaseAIReplyGenerator
from app.core.reply_generators.groq_reply_generator import GroqReplyGenerator
from app.core.validation.groq_validator import GroqValidator, BaseContentValidator


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432

    ELASTICSEARCH_URL: str = "http://elasticsearch:9200"

    SECRET_KEY: str
    EMAIL_TOKEN_SALT: str
    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    TOKEN_TYPES: list = ["access", "refresh"]

    OPENAI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None

    CONTENT_VALIDATOR_CLASS: Type[BaseContentValidator] = GroqValidator
    REPLY_GENERATOR_CLASS: Type[BaseAIReplyGenerator] = GroqReplyGenerator

    REDIS_HOST: str | None = "localhost"
    REDIS_PORT: int = 6379

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_USER_PASSWORD: str

    KAFKA_URL: str

    model_config: ClassVar[ConfigDict] = ConfigDict(
        env_file=".env",
    )

    @property
    def database_url(self) -> str:
        return (f"postgresql+asyncpg://{self.POSTGRES_USER}"
                f":{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}"
                f":5432/{self.POSTGRES_DB}")

    @property
    def test_database_url(self) -> str:
        return "sqlite+aiosqlite:///./test_database.db"

    @property
    def celery_broker_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def redis_cache_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"


settings = Settings()
