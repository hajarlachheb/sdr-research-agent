"""LLM setup with Helicone monitoring."""

import os

from langchain_openai import ChatOpenAI

from app.config import settings


def get_llm(model: str = "gpt-4o-mini", temperature: float = 0.3) -> ChatOpenAI:
    """Create LLM with optional Helicone proxy for monitoring."""
    kwargs = {
        "model": model,
        "temperature": temperature,
        "api_key": settings.openai_api_key or os.getenv("OPENAI_API_KEY"),
    }
    if settings.helicone_api_key or os.getenv("HELICONE_API_KEY"):
        kwargs["base_url"] = "https://oai.hconeai.com/v1"
        kwargs["default_headers"] = {
            "Helicone-Auth": f"Bearer {settings.helicone_api_key or os.getenv('HELICONE_API_KEY')}"
        }
    elif settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url

    return ChatOpenAI(**kwargs)
