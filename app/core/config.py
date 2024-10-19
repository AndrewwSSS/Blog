from pydantic import BaseSettings


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"

    @property
    def database_url(self) -> str:
        return (f"postgresql://{self.POSTGRES_USER}:"
                f"{self.POSTGRES_PASSWORD}@"
                f"{self.POSTGRES_HOST}:5432/{self.POSTGRES_DB}")


settings = Settings()