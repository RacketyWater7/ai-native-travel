from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://travel:travel@localhost:5432/travel"
    redis_url: str = "redis://localhost:6379/0"
    gemini_api_key: str | None = None
    cors_origins: str = "http://localhost:3000"
    app_env: str = "local"
    mock_llm: bool = Field(default=True, validation_alias="MOCK_LLM")

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
