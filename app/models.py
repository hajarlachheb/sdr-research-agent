"""Pydantic models for API and agent state."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    RESEARCHING = "researching"
    WRITING = "writing"
    CRITIQUING = "critiquing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchRequest(BaseModel):
    """Input for research job."""

    company_url: str = Field(..., description="Company domain URL (e.g., https://stripe.com)")
    company_name: str | None = Field(None, description="Optional company name override")
    ceo_name: str | None = Field(None, description="Optional CEO name for LinkedIn search")


class NewsArticle(BaseModel):
    """Scraped news/press release."""

    title: str
    url: str
    snippet: str
    published_date: str | None = None
    source: str = "web"


class LinkedInPost(BaseModel):
    """CEO LinkedIn post (placeholder - real integration requires LinkedIn API)."""

    content: str
    posted_date: str | None = None
    engagement: str | None = None


class ResearchData(BaseModel):
    """Collected research from Researcher agent."""

    company_name: str
    company_url: str
    news_articles: list[NewsArticle] = Field(default_factory=list)
    linkedin_posts: list[LinkedInPost] = Field(default_factory=list)
    company_summary: str = ""
    key_topics: list[str] = Field(default_factory=list)
    raw_content: str = ""


class CritiqueResult(BaseModel):
    """Critic agent output."""

    score: float = Field(ge=0, le=1, description="Quality score 0-1")
    passed: bool = False
    feedback: str = ""
    suggestions: list[str] = Field(default_factory=list)


class EmailDraft(BaseModel):
    """Writer agent output."""

    subject: str
    body: str
    personalization_notes: str = ""


class AgentState(BaseModel):
    """Shared state across LangGraph agents."""

    company_url: str
    company_name: str = ""
    research: ResearchData | None = None
    email_draft: EmailDraft | None = None
    critique: CritiqueResult | None = None
    round: int = 0
    messages: list[dict[str, Any]] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


class JobResult(BaseModel):
    """Final job output."""

    job_id: str
    status: JobStatus
    company_url: str
    research: ResearchData | None = None
    email_draft: EmailDraft | None = None
    critique_rounds: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error: str | None = None
