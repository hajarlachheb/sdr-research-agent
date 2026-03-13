"""Application configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env path relative to project root (parent of app/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM - use "groq" or "ollama" for free models
    llm_provider: str = "groq"  # openai | groq | ollama
    openai_api_key: str = ""
    openai_base_url: str | None = None  # Helicone proxy
    groq_api_key: str = ""  # Free at console.groq.com

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
    research_cache_ttl_seconds: int = 172800  # 48 hours


settings = Settings()
