"""Researcher Agent - Scrapes company news and gathers intel."""

import asyncio

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.models import ResearchData
from app.models import LinkedInPost
from app.services.job_queue import get_research_cache, set_research_cache
from app.services.scraper import (
    extract_domain,
    scrape_company,
    search_ceo_mentions,
    search_company_news,
)
from app.agents.llm import get_llm


RESEARCHER_SYSTEM = """You are an expert Sales Development Researcher. Analyze company content and output JSON:
{
  "company_name": "string",
  "company_summary": "2-3 sentence summary",
  "key_topics": ["topic1", "topic2", "topic3"]
}
Be concise. Focus on what matters for cold email personalization."""


async def researcher_node(state: dict) -> dict:
    """Research agent: scrape + DuckDuckGo search + LLM analysis."""
    company_url = state["company_url"]
    company_name_override = state.get("company_name") or ""
    domain = extract_domain(company_url)
    company_for_search = company_name_override or domain

    # Check cache (by domain)
    cached = get_research_cache(domain)
    if cached is not None:
        return {
            **state,
            "research": cached,
            "company_name": cached.company_name,
            "messages": state.get("messages", []) + [{"role": "researcher", "content": "Served from cache"}],
        }

    # Scrape, search news, and optionally CEO mentions in parallel
    ceo_name = (state.get("ceo_name") or "").strip()
    if ceo_name:
        scraped, search_results, ceo_mentions = await asyncio.gather(
            scrape_company(company_url, settings.firecrawl_api_key),
            search_company_news(company_for_search, max_results=5),
            search_ceo_mentions(ceo_name, company_for_search, 3),
        )
    else:
        scraped, search_results = await asyncio.gather(
            scrape_company(company_url, settings.firecrawl_api_key),
            search_company_news(company_for_search, max_results=5),
        )
        ceo_mentions = []

    # Merge: scraped first, then search results not already covered (by URL)
    seen_urls = {a.url for a in scraped}
    articles = list(scraped)
    for a in search_results:
        if a.url and a.url not in seen_urls:
            seen_urls.add(a.url)
            articles.append(a)

    linkedin_posts = [LinkedInPost(content=m["content"]) for m in ceo_mentions]

    if not articles:
        research = ResearchData(
            company_name=company_name_override or extract_domain(company_url),
            company_url=company_url,
            news_articles=[],
            linkedin_posts=linkedin_posts,
            company_summary="No content could be scraped.",
            key_topics=[],
            raw_content="",
        )
        set_research_cache(domain, research)
        return {
            **state,
            "research": research,
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
            linkedin_posts=linkedin_posts,
            company_summary=data.get("company_summary", raw_content[:500]),
            key_topics=data.get("key_topics", []),
            raw_content=raw_content,
        )
    except Exception:
        research = ResearchData(
            company_name=company_name_override or extract_domain(company_url),
            company_url=company_url,
            news_articles=articles,
            linkedin_posts=linkedin_posts,
            company_summary=raw_content[:500],
            key_topics=[],
            raw_content=raw_content,
        )

    set_research_cache(domain, research)
    return {
        **state,
        "research": research,
        "company_name": research.company_name,
        "messages": state.get("messages", []) + [{"role": "researcher", "content": f"Found {len(articles)} articles"}],
    }
