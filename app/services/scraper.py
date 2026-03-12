"""Web scraping service - Firecrawl with BeautifulSoup fallback."""

import asyncio
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.models import NewsArticle


def extract_domain(url: str) -> str:
    """Extract domain from URL (e.g., stripe.com)."""
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    return domain.replace("www.", "").split("/")[0]


def _scrape_firecrawl_sync(url: str, api_key: str) -> list[NewsArticle]:
    """Sync Firecrawl scrape - runs in thread."""
    try:
        from firecrawl import FirecrawlApp

        app = FirecrawlApp(api_key=api_key)
        result = app.scrape_url(url)

        if not result or not result.get("success"):
            return []

        content = result.get("markdown", result.get("content", ""))
        metadata = result.get("metadata", {})
        company_name = metadata.get("title", extract_domain(url))

        if content:
            return [
                NewsArticle(
                    title=company_name,
                    url=url,
                    snippet=content[:2000],
                    source="firecrawl",
                )
            ]
        return []

    except ImportError:
        raise RuntimeError("firecrawl-py not installed. pip install firecrawl-py") from None
    except Exception as e:
        raise RuntimeError(f"Firecrawl scrape failed: {e}") from e


async def scrape_with_firecrawl(url: str, api_key: str) -> list[NewsArticle]:
    """Scrape URL using Firecrawl API (firecrawl.dev)."""
    return await asyncio.to_thread(_scrape_firecrawl_sync, url, api_key)


async def scrape_with_httpx(url: str) -> list[NewsArticle]:
    """Fallback: scrape with httpx + BeautifulSoup when Firecrawl unavailable."""
    domain = extract_domain(url)
    articles = []

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script/style
        for tag in soup(["script", "style"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)[:5000]

        # Try to find news links
        news_keywords = ["news", "press", "blog", "announcement"]
        for link in soup.find_all("a", href=True)[:20]:
            href = link.get("href", "")
            link_text = link.get_text(strip=True).lower()
            if any(kw in href.lower() or kw in link_text for kw in news_keywords):
                full_url = href if href.startswith("http") else f"https://{domain}{href}"
                articles.append(
                    NewsArticle(
                        title=link_text or "Link",
                        url=full_url,
                        snippet=text[:500],
                        source="scrape",
                    )
                )

        if not articles:
            articles.append(
                NewsArticle(
                    title=domain,
                    url=url,
                    snippet=text[:2000],
                    source="scrape",
                )
            )

        return articles

    except Exception as e:
        raise RuntimeError(f"Scrape failed: {e}") from e


async def scrape_company(url: str, firecrawl_api_key: str | None = None) -> list[NewsArticle]:
    """Scrape company URL - use Firecrawl if key present, else fallback."""
    if firecrawl_api_key:
        try:
            return await scrape_with_firecrawl(url, firecrawl_api_key)
        except Exception:
            pass  # Fall through to httpx
    return await scrape_with_httpx(url)
