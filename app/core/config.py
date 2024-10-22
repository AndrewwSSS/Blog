from typing import Type

from pydantic_settings import BaseSettings
from app.core.validation.groq_validator import GroqValidator, BaseContentValidator


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    ALGORITHM: str = "HS256"
    POSTGRES_PORT: int = 5432
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    TOKEN_TYPES: list = ["access", "refresh"]
    OPENAI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    CONTENT_VALIDATOR_CLASS: Type[BaseContentValidator] = GroqValidator

    class Config:
        env_file = ".env"

    @property
    def database_url(self) -> str:
        return (f"postgresql+asyncpg://{self.POSTGRES_USER}"
                f":{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}"
                f":5432/{self.POSTGRES_DB}")


settings = Settings()
