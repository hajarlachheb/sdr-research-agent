"""Redis-backed job queue for async research processing."""

import json
import uuid
from typing import Any

import redis
from redis import Redis

from app.config import settings
from app.models import JobStatus, ResearchData, EmailDraft


def get_redis() -> Redis:
    """Get Redis client."""
    return redis.from_url(settings.redis_url, decode_responses=True)


def enqueue_research(company_url: str, company_name: str | None = None, ceo_name: str | None = None) -> str:
    """Enqueue a research job. Returns job_id."""
    r = get_redis()
    job_id = str(uuid.uuid4())
    payload = {
        "company_url": company_url,
        "company_name": company_name,
        "ceo_name": ceo_name,
    }
    r.set(f"job:{job_id}", json.dumps({"status": JobStatus.PENDING.value, "payload": payload}))
    r.lpush("queue:research", job_id)
    return job_id


def get_job(job_id: str) -> dict[str, Any] | None:
    """Get job state."""
    r = get_redis()
    data = r.get(f"job:{job_id}")
    if not data:
        return None
    return json.loads(data)


def update_job(job_id: str, **kwargs) -> None:
    """Update job state."""
    r = get_redis()
    data = get_job(job_id) or {}
    data.update(kwargs)
    r.set(f"job:{job_id}", json.dumps(data))


def dequeue_job() -> str | None:
    """Pop next job from queue. Returns job_id or None."""
    r = get_redis()
    return r.rpop("queue:research")


def set_job_result(job_id: str, research: ResearchData | None, draft: EmailDraft | None, rounds: int, error: str | None = None) -> None:
    """Store final job result."""
    update_job(
        job_id,
        status=JobStatus.COMPLETED.value if not error else JobStatus.FAILED.value,
        research=research.model_dump() if research else None,
        email_draft=draft.model_dump() if draft else None,
        critique_rounds=rounds,
        error=error,
    )


# ---- Research cache (by domain) ----

RESEARCH_CACHE_PREFIX = "research:"


def get_research_cache(domain: str) -> ResearchData | None:
    """Return cached ResearchData for domain, or None."""
    try:
        r = get_redis()
        raw = r.get(f"{RESEARCH_CACHE_PREFIX}{domain}")
        if not raw:
            return None
        return ResearchData.model_validate(json.loads(raw))
    except Exception:
        return None


def set_research_cache(domain: str, research: ResearchData, ttl_seconds: int | None = None) -> None:
    """Cache research by domain. TTL from settings if not provided."""
    try:
        r = get_redis()
        key = f"{RESEARCH_CACHE_PREFIX}{domain}"
        r.set(key, json.dumps(research.model_dump()))
        r.expire(key, ttl_seconds if ttl_seconds is not None else settings.research_cache_ttl_seconds)
    except Exception:
        pass
