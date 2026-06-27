"""
LangGraph StateGraph construction and compilation.

Builds the multi-agent pipeline graph with conditional routing:
  START → harm_assessment → supervisor → [conditional]
    - is_safe=True  → rag_agent → response_agent → END
    - is_safe=False → END (refusal path)
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, START, END

from src.agents.state import AgentState
from src.agents.nodes.harm_assessment import harm_assessment_node
from src.agents.nodes.supervisor import supervisor_node
from src.agents.nodes.rag_agent import rag_agent_node
from src.agents.nodes.response_agent import response_agent_node

logger = logging.getLogger(__name__)


def _route_after_supervisor(state: AgentState) -> str:
    """
    Conditional routing after Supervisor node.

    If the question was assessed as safe by Harm Assessment,
    route to RAG Agent. Otherwise, route directly to END
    (the refusal message is already in state from Harm Assessment).
    """
    is_safe = state.get("is_safe", True)

    if is_safe:
        logger.info("Routing: supervisor → rag_agent (SAFE)")
        return "rag_agent"
    else:
        logger.info("Routing: supervisor → END (UNSAFE)")
        return END


def build_graph() -> StateGraph:
    """
    Build and compile the multi-agent StateGraph.

    Graph topology (from data-model.md):
        START → harm_assessment → supervisor → [is_safe?]
          Yes → rag_agent → response_agent → END
          No  → END
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

    # Conditional edge after supervisor: safe → rag_agent, unsafe → END
    graph.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        {
            "rag_agent": "rag_agent",
            END: END,
        },
    )

    # Sequential edges: rag_agent → response_agent → END
    graph.add_edge("rag_agent", "response_agent")
    graph.add_edge("response_agent", END)

    logger.info("StateGraph built successfully")
    return graph


def compile_graph():
    """Build and compile the graph, returning a runnable."""
    graph = build_graph()
    return graph.compile()
