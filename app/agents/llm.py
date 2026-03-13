"""LLM setup - supports OpenAI, Groq (free), and Ollama (local)."""

import os
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import settings


def get_llm(
    model: str | None = None,
    temperature: float = 0.3,
) -> BaseChatModel:
    """Create LLM. Uses Groq (free) by default, or OpenAI/Ollama per config."""
    provider = (settings.llm_provider or os.getenv("LLM_PROVIDER", "groq")).lower()

    if provider == "ollama":
        from langchain_community.chat_models import ChatOllama

        return ChatOllama(
            model=model or "llama3.2",
            temperature=temperature,
        )

    if provider == "groq":
        api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "Groq API key required. Get free key at https://console.groq.com "
                "and set GROQ_API_KEY in .env"
            )
        return ChatOpenAI(
            model=model or "llama-3.1-8b-instant",
            temperature=temperature,
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )

    # OpenAI (default when provider=openai)
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key required. Set OPENAI_API_KEY in .env")
    kwargs = {
        "model": model or "gpt-4o-mini",
        "temperature": temperature,
        "api_key": api_key,
    }
    if settings.helicone_api_key or os.getenv("HELICONE_API_KEY"):
        kwargs["base_url"] = "https://oai.hconeai.com/v1"
        kwargs["default_headers"] = {
            "Helicone-Auth": f"Bearer {settings.helicone_api_key or os.getenv('HELICONE_API_KEY')}"
        }
    elif settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url

    return ChatOpenAI(**kwargs)
