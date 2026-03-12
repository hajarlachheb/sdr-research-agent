"""Background worker - processes research jobs from Redis queue."""

import asyncio

from app.agents.graph import create_research_graph
from app.models import JobStatus
from app.services.job_queue import dequeue_job, get_job, set_job_result, update_job


async def process_one_job() -> bool:
    """Process a single job from the queue. Returns True if a job was processed."""
    job_id = dequeue_job()
    if not job_id:
        return False

    job = get_job(job_id)
    if not job or job.get("status") != JobStatus.PENDING.value:
        return False

    payload = job.get("payload", {})
    company_url = payload.get("company_url", "")
    if not company_url:
        set_job_result(job_id, None, None, 0, error="Missing company_url")
        return True

    try:
        update_job(job_id, status=JobStatus.RESEARCHING.value)

        graph = create_research_graph()
        config = {"configurable": {"thread_id": job_id}}

        initial_state = {
            "company_url": company_url,
            "company_name": payload.get("company_name"),
            "ceo_name": payload.get("ceo_name"),
            "messages": [],
        }

        final_state = await graph.ainvoke(initial_state, config=config)

        if final_state:
            research = final_state.get("research")
            draft = final_state.get("email_draft")
            rounds = final_state.get("round", 0)
            set_job_result(job_id, research, draft, rounds)
        else:
            set_job_result(job_id, None, None, 0, error="No final state")

    except Exception as e:
        set_job_result(job_id, None, None, 0, error=str(e))

    return True


async def run_worker():
    """Run worker loop."""
    while True:
        try:
            processed = await process_one_job()
            if not processed:
                await asyncio.sleep(2)
        except Exception as e:
            print(f"Worker error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run_worker())
