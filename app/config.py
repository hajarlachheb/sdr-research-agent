"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    openai_api_key: str = ""
    openai_base_url: str | None = None  # Helicone proxy

    # Scraping
    firecrawl_api_key: str | None = None

    # Infrastructure
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/sdr_agent"

    # Monitoring
    helicone_api_key: str | None = None

    # Agent settings
    max_critique_rounds: int = 3
    quality_threshold: float = 0.8


settings = Settings()
