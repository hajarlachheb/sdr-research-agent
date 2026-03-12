"""Writer Agent - Generates personalized cold email drafts."""

from langchain_core.messages import HumanMessage, SystemMessage

from app.models import CritiqueResult, EmailDraft, ResearchData
from app.agents.llm import get_llm


WRITER_SYSTEM = """You are an expert cold email copywriter for B2B sales. Your emails:
- Are personalized based on recent company news and activity
- Open with a specific, relevant hook (not generic)
- Are concise: 3-4 short paragraphs max, under 150 words
- Have a clear, low-friction CTA
- Sound human, not AI-generated
- Avoid buzzwords and corporate speak

Output valid JSON with: subject, body, personalization_notes"""


async def writer_node(state: dict) -> dict:
    """Writer agent: generate email draft from research."""
    research: ResearchData = state["research"]
    critique: CritiqueResult | None = state.get("critique")
    round_num = state.get("round", 0)

    llm = get_llm(temperature=0.5)

    research_context = f"""
Company: {research.company_name}
Summary: {research.company_summary}
Key topics: {", ".join(research.key_topics) if research.key_topics else "N/A"}

Recent news/snippets:
"""
    for a in research.news_articles[:5]:
        research_context += f"\n- {a.title}: {a.snippet[:200]}..."

    if research.linkedin_posts:
        research_context += "\n\nCEO/Leadership posts:\n"
        for p in research.linkedin_posts[:3]:
            research_context += f"- {p.content[:300]}...\n"

    prompt = f"""{WRITER_SYSTEM}

Research context:
{research_context}

Generate a personalized cold email to the CEO/decision maker at {research.company_name}.
"""
    if critique and round_num > 0:
        prompt += f"""

Previous draft was critiqued. Apply this feedback:
Score: {critique.score}
Feedback: {critique.feedback}
Suggestions: {"; ".join(critique.suggestions)}
"""

    response = await llm.ainvoke([
        SystemMessage(content=WRITER_SYSTEM),
        HumanMessage(content=prompt),
    ])

    text = response.content
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        draft = EmailDraft.model_validate_json(text)
    except Exception:
        # Fallback parse
        draft = EmailDraft(
            subject="Quick question",
            body=text[:1500] if len(text) > 1500 else text,
            personalization_notes="",
        )

    return {
        **state,
        "email_draft": draft,
        "messages": state.get("messages", []) + [{"role": "writer", "content": "Draft generated"}],
    }
