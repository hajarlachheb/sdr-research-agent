# Automated SDR Research Agent

> Sales Development Reps (SDRs) are drowning in manual work. This agent automates the most boring part of the sales process—research and personalization—so expensive humans can focus on closing deals.

## Overview

An AI-powered multi-agent system that:
1. Takes a company domain URL as input
2. Scrapes latest news/press releases
3. Finds the CEO's LinkedIn posts
4. Generates highly personalized cold email drafts based on recent activity

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Researcher │────▶│   Critic    │────▶│   Writer    │
│   Agent     │     │   Agent     │     │   Agent     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
  Firecrawl/Scrape    Quality Check         Email Draft
  pgvector store      Loop until OK         Output
```

## Tech Stack

- **Orchestration**: LangGraph (multi-agent workflows)
- **Vector Store**: pgvector (embeddings & retrieval)
- **Job Queue**: Redis (parallel processing)
- **API**: FastAPI (structured JSON validation via Pydantic)
- **Monitoring**: Helicone (LLM execution logging)
- **Scraping**: Firecrawl / BeautifulSoup fallback

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (copy .env.example to .env)
cp .env.example .env

# Run Redis (Docker)
docker run -d -p 6379:6379 redis:alpine

# Run PostgreSQL with pgvector
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres ankane/pgvector

# Start the API
uvicorn app.main:app --reload

# Or use Streamlit UI
streamlit run app/ui/streamlit_app.py
```

## API Usage

```bash
# Submit research job
curl -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{"company_url": "https://stripe.com"}'

# Get job status
curl http://localhost:8000/api/v1/jobs/{job_id}

# Get result
curl http://localhost:8000/api/v1/jobs/{job_id}/result
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (for LLM) |
| `FIRECRAWL_API_KEY` | Firecrawl API key (optional, for scraping) |
| `REDIS_URL` | Redis connection URL |
| `DATABASE_URL` | PostgreSQL + pgvector connection |
| `HELICONE_API_KEY` | Helicone for LLM monitoring |

## License

MIT
