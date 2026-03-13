"""Web scraping service - Firecrawl with BeautifulSoup fallback."""

import asyncio
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.models import NewsArticle

# Max number of news/blog links to follow and scrape
MAX_LINKS_TO_FOLLOW = 5


def extract_domain(url: str) -> str:
    """Extract domain from URL (e.g., stripe.com)."""
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    return domain.replace("www.", "").split("/")[0]


async def _fetch_page_text(client: httpx.AsyncClient, url: str) -> tuple[str, str]:
    """Fetch a single URL and return (title_or_url, text_snippet)."""
    try:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)[:2000]
        title = url
        if soup.title and soup.title.string:
            title = soup.title.string.strip()[:200]
        return title, text
    except Exception:
        return url, ""


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
    """Scrape homepage, find news/blog links, and fetch those pages for real content."""
    domain = extract_domain(url)
    base_scheme = urlparse(url).scheme or "https"
    base_netloc = urlparse(url).netloc or domain

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style"]):
                tag.decompose()

            homepage_text = soup.get_text(separator=" ", strip=True)
            homepage_text = re.sub(r"\s+", " ", homepage_text)[:5000]

            # Collect news/blog link URLs (same domain only)
            news_keywords = ["news", "press", "blog", "announcement", "insights", "article"]
            links_to_fetch: list[tuple[str, str]] = []  # (full_url, link_text)

            for link in soup.find_all("a", href=True):
                href = link.get("href", "").strip()
                if not href or href.startswith("#") or href.startswith("mailto:"):
                    continue
                full_url = urljoin(f"{base_scheme}://{base_netloc}", href)
                if extract_domain(full_url) != domain:
                    continue
                link_text = link.get_text(strip=True).lower()
                if any(kw in href.lower() or kw in link_text for kw in news_keywords):
                    links_to_fetch.append((full_url, link_text or "Article"))
                    if len(links_to_fetch) >= MAX_LINKS_TO_FOLLOW:
                        break

            articles: list[NewsArticle] = []
            seen_urls: set[str] = set()

            # Fetch linked pages and scrape content
            for full_url, link_label in links_to_fetch[:MAX_LINKS_TO_FOLLOW]:
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                title, snippet = await _fetch_page_text(client, full_url)
                if snippet:
                    articles.append(
                        NewsArticle(
                            title=title or link_label,
                            url=full_url,
                            snippet=snippet,
                            source="scrape",
                        )
                    )

            # Always add homepage as first or only source
            if not articles:
                articles.append(
                    NewsArticle(
                        title=domain,
                        url=url,
                        snippet=homepage_text[:2000],
                        source="scrape",
                    )
                )
            else:
                # Prepend homepage summary so we have company overview
                articles.insert(
                    0,
                    NewsArticle(
                        title=f"{domain} (overview)",
                        url=url,
                        snippet=homepage_text[:1500],
                        source="scrape",
                    ),
                )

            return articles

    except Exception as e:
        raise RuntimeError(f"Scrape failed: {e}") from e


def search_company_news_sync(company_name: str, max_results: int = 5) -> list[NewsArticle]:
    """Search DuckDuckGo for recent company news (no API key). Runs in thread for async."""
    try:
        from duckduckgo_search import DDGS

        query = f'"{company_name}" news OR announcement 2024 2025'
        articles = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                articles.append(
                    NewsArticle(
                        title=r.get("title", "Result"),
                        url=r.get("href", ""),
                        snippet=(r.get("body") or "")[:500],
                        source="duckduckgo",
                    )
                )
        return articles
    except ImportError:
        return []
    except Exception:
        return []


async def search_company_news(company_name: str, max_results: int = 5) -> list[NewsArticle]:
    """Async wrapper for DuckDuckGo company news search."""
    return await asyncio.to_thread(search_company_news_sync, company_name, max_results)


def search_ceo_mentions_sync(ceo_name: str, company_name: str, max_results: int = 3) -> list[dict]:
    """Search for CEO/exec mentions (quotes, interviews). Returns list of {content, url}."""
    try:
        from duckduckgo_search import DDGS

        query = f'"{ceo_name}" "{company_name}"'
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                body = (r.get("body") or "").strip()
                if body:
                    results.append({"content": body[:400], "url": r.get("href", "")})
        return results
    except (ImportError, Exception):
        return []


async def search_ceo_mentions(ceo_name: str, company_name: str, max_results: int = 3) -> list[dict]:
    """Async wrapper for CEO mention search."""
    return await asyncio.to_thread(search_ceo_mentions_sync, ceo_name, company_name, max_results)


async def scrape_company(url: str, firecrawl_api_key: str | None = None) -> list[NewsArticle]:
    """Scrape company URL - use Firecrawl if key present, else fallback."""
    if firecrawl_api_key:
        try:
            return await scrape_with_firecrawl(url, firecrawl_api_key)
        except Exception:
            pass  # Fall through to httpx
    return await scrape_with_httpx(url)
