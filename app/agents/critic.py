"""Critic Agent - Evaluates email quality and provides feedback."""

from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.models import CritiqueResult, EmailDraft, ResearchData
from app.agents.llm import get_llm


CRITIC_SYSTEM = """You are a cold email quality critic. Evaluate emails on:
1. Personalization (0-1): Does it reference specific company news/activity?
2. Hook strength (0-1): Is the opening compelling and specific?
3. Conciseness (0-1): Is it under 150 words, scannable?
4. CTA clarity (0-1): Is the ask clear and low-friction?
5. Human tone (0-1): Does it sound natural, not AI-generated?

Output valid JSON with: score (average 0-1), passed (true if score >= 0.8), feedback (brief), suggestions (list of strings)"""


async def critic_node(state: dict) -> dict:
    """Critic agent: score draft and provide feedback."""
    research: ResearchData = state["research"]
    draft: EmailDraft = state["email_draft"]
    round_num = state.get("round", 0)

    llm = get_llm(temperature=0.2)

    prompt = f"""{CRITIC_SYSTEM}

Research used:
{research.company_summary}
Topics: {", ".join(research.key_topics)}

Email to evaluate:
Subject: {draft.subject}
Body:
{draft.body}

Output JSON only."""

    response = await llm.ainvoke([
        SystemMessage(content=CRITIC_SYSTEM),
        HumanMessage(content=prompt),
    ])

    text = response.content
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        critique = CritiqueResult.model_validate_json(text)
    except Exception:
        critique = CritiqueResult(
            score=0.7,
            passed=True,
            feedback="Could not parse critique; accepting draft.",
            suggestions=[],
        )

    return {
        **state,
        "critique": critique,
        "round": round_num + 1,
        "messages": state.get("messages", []) + [{"role": "critic", "content": f"Score: {critique.score}, Passed: {critique.passed}"}],
    }


def should_continue(state: dict) -> str:
    """Routing: continue to writer or end."""
    critique = state.get("critique")
    round_num = state.get("round", 0)
    max_rounds = settings.max_critique_rounds
    threshold = settings.quality_threshold

    if not critique:
        return "writer"

    if critique.passed or critique.score >= threshold:
        return "end"
    if round_num >= max_rounds:
        return "end"
    return "writer"
