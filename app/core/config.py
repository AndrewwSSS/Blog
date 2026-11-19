from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432

    # Tests drop all tables; a PostgreSQL test database name must end with "_test".
    TEST_DATABASE_URL: str = "sqlite+aiosqlite:///./test_database.db"

    ELASTICSEARCH_URL: str = "http://elasticsearch:9200"

    PUBLIC_BASE_URL: str = "http://127.0.0.1:8000"

    SECRET_KEY: str
    EMAIL_TOKEN_SALT: str
    EMAIL_TOKEN_EXPIRE_HOURS: int = 24
    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    TOKEN_TYPES: list = ["access", "refresh"]

    OPENAI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None

    CONTENT_VALIDATOR: Literal["groq", "openai"] = "groq"
    REPLY_GENERATOR: Literal["groq"] = "groq"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_USER_PASSWORD: str

    KAFKA_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}"
            f":{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}"
            f":{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def email_verification_url_prefix(self) -> str:
        return f"{self.PUBLIC_BASE_URL.rstrip('/')}/api/v1/users/verification/"

    @property
    def celery_broker_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def redis_cache_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"


settings = Settings()
