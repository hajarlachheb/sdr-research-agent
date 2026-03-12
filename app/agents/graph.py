"""LangGraph workflow: Research -> Write -> Critic (loop until quality)."""

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.agents.researcher import researcher_node
from app.agents.writer import writer_node
from app.agents.critic import critic_node, should_continue


def create_research_graph():
    """Build the multi-agent research graph."""
    workflow = StateGraph(dict)

    workflow.add_node("researcher", researcher_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("critic", critic_node)

    workflow.set_entry_point("researcher")
    workflow.add_edge("researcher", "writer")
    workflow.add_edge("writer", "critic")
    workflow.add_conditional_edges("critic", should_continue, {"writer": "writer", "end": END})

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
