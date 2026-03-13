#!/usr/bin/env python3
"""Convenience runner - sync research without Redis for quick testing."""

import asyncio
import sys
import uuid

from app.agents.graph import create_research_graph


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://stripe.com"
    print(f"Researching {url}...")

    graph = create_research_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    state = await graph.ainvoke({
        "company_url": url,
        "company_name": None,
        "ceo_name": None,
        "messages": [],
    }, config=config)

    research = state.get("research")
    draft = state.get("email_draft")

    if research:
        print("\n--- Research ---")
        print(research.company_summary)
        print("Topics:", research.key_topics)

    if draft:
        print("\n--- Email Draft ---")
        print("Subject:", draft.subject)
        print("\nBody:\n", draft.body)


if __name__ == "__main__":
    asyncio.run(main())
