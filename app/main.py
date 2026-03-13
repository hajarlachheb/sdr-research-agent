"""FastAPI application for SDR Research Agent."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.models import JobStatus, ResearchData, EmailDraft
from app.services.job_queue import enqueue_research, get_job
from app.agents.graph import create_research_graph

app = FastAPI(
    title="SDR Research Agent API",
    description="Multi-agent system for personalized cold email generation",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    company_url: str
    company_name: str | None = None
    ceo_name: str | None = None


class ResearchResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    company_url: str | None
    research: dict | None
    email_draft: dict | None
    critique_rounds: int
    error: str | None


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/api/v1/research", response_model=ResearchResponse)
async def submit_research(req: ResearchRequest):
    """Submit a research job. Returns job_id for polling."""
    job_id = enqueue_research(req.company_url, req.company_name, req.ceo_name)
    return ResearchResponse(
        job_id=job_id,
        status=JobStatus.PENDING.value,
        message="Job queued. Poll /api/v1/jobs/{job_id} for status.",
    )


@app.get("/api/v1/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get job status and result."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        company_url=job.get("payload", {}).get("company_url"),
        research=job.get("research"),
        email_draft=job.get("email_draft"),
        critique_rounds=job.get("critique_rounds", 0),
        error=job.get("error"),
    )


@app.post("/api/v1/research/sync")
async def research_sync(req: ResearchRequest):
    """Run research synchronously (no Redis). Useful for quick testing."""
    graph = create_research_graph()
    initial_state = {
        "company_url": req.company_url,
        "company_name": req.company_name,
        "ceo_name": req.ceo_name,
        "messages": [],
    }
    try:
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        final_state = await graph.ainvoke(initial_state, config=config)
        return {
            "research": final_state.get("research"),
            "email_draft": final_state.get("email_draft"),
            "rounds": final_state.get("round", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
