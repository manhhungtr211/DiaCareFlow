"""
LangGraph StateGraph construction and compilation.

Builds the multi-agent pipeline graph with conditional routing:
  START → harm_assessment → supervisor → [conditional]
    - is_safe=False              → END (refusal path)
    - intent=SMALL_TALK          → response_agent → END (bypass RAG)
    - intent=DIABETES (default)  → rag_agent → response_agent → END

UC-009: Graph is compiled with MemorySaver checkpointer for per-session
chat history persistence. Pass config={"configurable": {"thread_id": ...}}
when invoking the compiled graph.
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.agents.state import AgentState
from src.agents.nodes.harm_assessment import harm_assessment_node
from src.agents.nodes.supervisor import supervisor_node
from src.agents.nodes.rag_agent import rag_agent_node
from src.agents.nodes.response_agent import response_agent_node

logger = logging.getLogger(__name__)


def _route_after_supervisor(state: AgentState) -> str:
    """
    Conditional routing after Supervisor node.

    Three-way routing based on safety and intent:
      - is_safe=False → END (refusal message already in state)
      - intent=SMALL_TALK → response_agent (bypass RAG)
      - intent=DIABETES → rag_agent (full RAG pipeline)
    """
    is_safe = state.get("is_safe", True)

    if not is_safe:
        logger.info("Routing: supervisor → END (UNSAFE)")
        return END

    intent = state.get("intent", "DIABETES")

    if intent == "SMALL_TALK":
        logger.info("Routing: supervisor → response_agent (SMALL_TALK, bypass RAG)")
        return "response_agent"
    else:
        logger.info("Routing: supervisor → rag_agent (DIABETES)")
        return "rag_agent"


def build_graph() -> StateGraph:
    """
    Build and compile the multi-agent StateGraph.

    Graph topology (UC-010 data-model.md):
        START → harm_assessment → supervisor → [conditional]
          UNSAFE     → END
          SMALL_TALK → response_agent → END
          DIABETES   → rag_agent → response_agent → END
    """
    logger.info("Building LangGraph StateGraph (4-node pipeline)")

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("harm_assessment", harm_assessment_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("rag_agent", rag_agent_node)
    graph.add_node("response_agent", response_agent_node)

    # Add edges: START → harm_assessment → supervisor
    graph.add_edge(START, "harm_assessment")
    graph.add_edge("harm_assessment", "supervisor")

    # Conditional edge after supervisor: 3-way routing
    graph.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        {
            "rag_agent": "rag_agent",
            "response_agent": "response_agent",
            END: END,
        },
    )

    # Sequential edges: rag_agent → response_agent → END
    graph.add_edge("rag_agent", "response_agent")
    graph.add_edge("response_agent", END)

    logger.info("StateGraph built successfully")
    return graph


def compile_graph(checkpointer=None):
    """
    Build and compile the graph, returning a runnable.

    Args:
        checkpointer: Optional checkpointer for state persistence.
                      Defaults to MemorySaver for in-memory session history.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()
    graph = build_graph()
    return graph.compile(checkpointer=checkpointer)
