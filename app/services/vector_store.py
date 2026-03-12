"""Vector store for research embeddings - pgvector with in-memory fallback."""

from typing import Any

# Lazy pgvector - optional dependency
_pgvector_available = False
try:
    from pgvector.sqlalchemy import Vector  # noqa: F401
    from sqlalchemy import create_engine, text  # noqa: F401
    from sqlalchemy.orm import declarative_base, Session  # noqa: F401

    _pgvector_available = True
except ImportError:
    pass


class InMemoryVectorStore:
    """Simple in-memory store when pgvector not configured."""

    def __init__(self):
        self._store: dict[str, list[dict[str, Any]]] = {}

    def add(self, key: str, documents: list[dict[str, Any]]) -> None:
        self._store[key] = documents

    def search(self, key: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        docs = self._store.get(key, [])
        return docs[:top_k]


def get_vector_store(database_url: str | None = None) -> InMemoryVectorStore:
    """Get vector store - pgvector if DB configured, else in-memory."""
    if _pgvector_available and database_url and "postgresql" in database_url:
        # TODO: Full pgvector implementation with embeddings
        # For MVP, use in-memory
        pass
    return InMemoryVectorStore()
