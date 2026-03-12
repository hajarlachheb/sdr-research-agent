"""Researcher Agent - Scrapes company news and gathers intel."""

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.models import ResearchData
from app.services.scraper import extract_domain, scrape_company
from app.agents.llm import get_llm


RESEARCHER_SYSTEM = """You are an expert Sales Development Researcher. Analyze company content and output JSON:
{
  "company_name": "string",
  "company_summary": "2-3 sentence summary",
  "key_topics": ["topic1", "topic2", "topic3"]
}
Be concise. Focus on what matters for cold email personalization."""


async def researcher_node(state: dict) -> dict:
    """Research agent: scrape + LLM analysis."""
    company_url = state["company_url"]
    company_name_override = state.get("company_name") or ""

    # Scrape
    articles = await scrape_company(company_url, settings.firecrawl_api_key)

    if not articles:
        return {
            **state,
            "research": ResearchData(
                company_name=company_name_override or extract_domain(company_url),
                company_url=company_url,
                news_articles=[],
                company_summary="No content could be scraped.",
                key_topics=[],
                raw_content="",
            ),
            "messages": state.get("messages", []) + [{"role": "researcher", "content": "Scrape completed (no articles found)"}],
        }

    raw_content = "\n\n".join(
        f"## {a.title}\n{a.snippet}" for a in articles[:5]
    )

    # LLM analysis - simple JSON
    llm = get_llm(temperature=0.2)
    prompt = f"""Scraped content from {company_url}:
---
{raw_content[:8000]}
---

Output JSON with company_name, company_summary, key_topics."""
    if company_name_override:
        prompt += f"\nCompany name hint: {company_name_override}"

    response = await llm.ainvoke([
        SystemMessage(content=RESEARCHER_SYSTEM),
        HumanMessage(content=prompt),
    ])

    text = response.content
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        import json
        data = json.loads(text)
        research = ResearchData(
            company_name=data.get("company_name", company_name_override or extract_domain(company_url)),
            company_url=company_url,
            news_articles=articles,
            company_summary=data.get("company_summary", raw_content[:500]),
            key_topics=data.get("key_topics", []),
            raw_content=raw_content,
        )
    except Exception:
        research = ResearchData(
            company_name=company_name_override or extract_domain(company_url),
            company_url=company_url,
            news_articles=articles,
            company_summary=raw_content[:500],
            key_topics=[],
            raw_content=raw_content,
        )

    return {
        **state,
        "research": research,
        "company_name": research.company_name,
        "messages": state.get("messages", []) + [{"role": "researcher", "content": f"Found {len(articles)} articles"}],
    }
