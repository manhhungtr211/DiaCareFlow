"""
LangGraph StateGraph construction and compilation (UC-012).

Multi-Agent topology:
  START → triage_agent → [conditional]
    - is_safe=False  → response_agent → END  (refusal path, no sub-agents)
    - is_safe=True   → supervisor → [conditional]
        - intent=SMALL_TALK → response_agent → END  (bypass sub-agents)
        - intent=DIABETES   → factor_agent ─┐
                              suggestion_agent ─┤ → aggregate → response_agent → END
                              harm_sub_agent  ─┘

factor_agent / suggestion_agent / harm_sub_agent run in PARALLEL via Send API.
They fan-in through Annotated[list, operator.add] reducers on AgentState.

UC-009: Graph is compiled with MemorySaver checkpointer for per-session
chat history persistence. Pass config={"configurable": {"thread_id": ...}}
when invoking the compiled graph.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Send

from src.agents.state import AgentState
from src.agents.nodes.triage_node import triage_agent_node
from src.agents.nodes.supervisor import supervisor_node
from src.agents.nodes.response_agent import response_agent_node
from src.agents.nodes.factor_agent import factor_agent_node
from src.agents.nodes.suggestion_agent import suggestion_agent_node
from src.agents.nodes.harm_agent import harm_agent_node

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------


def _route_after_triage(state: AgentState) -> str:
    """
    Conditional routing after Triage Agent node (UC-012).

    Two-way routing based on safety:
      - is_safe=False → response_agent (refusal message already in state)
      - is_safe=True  → supervisor (intent classification + fan-out dispatch)
    """
    is_safe = state.get("is_safe", True)

    if not is_safe:
        logger.info("Routing: triage_agent → response_agent (UNSAFE)")
        return "response_agent"

    logger.info("Routing: triage_agent → supervisor")
    return "supervisor"


def _dispatch_sub_agents(state: AgentState) -> list[Send] | str:
    """
    Conditional routing / fan-out after Supervisor node (UC-012 T015).

    - intent=SMALL_TALK → route directly to response_agent (string return)
    - intent=DIABETES   → fan-out via Send to 3 parallel sub-agents (list return)
    """
    intent = state.get("intent", "DIABETES")

    if intent == "SMALL_TALK":
        logger.info("Routing: supervisor → response_agent (SMALL_TALK, bypass sub-agents)")
        return "response_agent"

    logger.info("Routing: supervisor → [factor_agent | suggestion_agent | harm_agent] (PARALLEL)")
    return [
        Send("factor_agent",    {"user_input": state.get("factor_question", state["user_input"]), "chat_history": state.get("chat_history", [])}),
        Send("suggestion_agent", {"user_input": state.get("suggestion_question", state["user_input"]), "chat_history": state.get("chat_history", [])}),
        Send("harm_agent",  {"user_input": state.get("harm_question", state["user_input"]), "chat_history": state.get("chat_history", [])}),
    ]


# ---------------------------------------------------------------------------
# Aggregate node (pure function, no LLM)
# ---------------------------------------------------------------------------


def aggregate_node(state: AgentState) -> dict[str, Any]:
    """
    Aggregate node — fan-in point after parallel sub-agents.

    By the time this node runs, LangGraph has already merged all three
    sub-agent results into state via operator.add reducers:
      - state["factor_results"]    from factor_agent
      - state["suggestion_results"] from suggestion_agent
      - state["harm_results"]    from harm_agent

    This node is a pure pass-through — it exists as an explicit
    synchronization point in the graph so response_agent has a
    single predecessor and can read the merged state safely.
    """
    factor_count = len(state.get("factor_results", []))
    suggestion_count = len(state.get("suggestion_results", []))
    harm_count = len(state.get("harm_results", []))
    error_count = len(state.get("errors", []))

    logger.info(
        f"Aggregate: fan-in complete — "
        f"factor={factor_count}, suggestion={suggestion_count}, "
        f"harm_sub={harm_count}, errors={error_count}"
    )
    return {"nodes_visited": ["aggregate"]}


# ---------------------------------------------------------------------------
# Graph construction (T015)
# ---------------------------------------------------------------------------


def build_graph() -> StateGraph:
    """
    Build and compile the multi-agent StateGraph (UC-012).

    Full topology:
        START → triage_agent → [conditional]
          UNSAFE     → response_agent → END
          SAFE       → supervisor → [conditional]
            SMALL_TALK → response_agent → END
            DIABETES   → factor_agent ─┐
                          suggestion_agent ─┤ → aggregate → response_agent → END
                          harm_sub_agent  ─┘
    """
    logger.info("Building LangGraph StateGraph (UC-012 full Multi-Agent topology)")

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("triage_agent", triage_agent_node)   # UC-012: renamed from harm_assessment
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("factor_agent", factor_agent_node)      # NEW
    graph.add_node("suggestion_agent", suggestion_agent_node)  # NEW
    graph.add_node("harm_agent", harm_agent_node)  # NEW
    graph.add_node("aggregate", aggregate_node)            # NEW
    graph.add_node("response_agent", response_agent_node)

    # START → triage_agent
    graph.add_edge(START, "triage_agent")

    # triage_agent → supervisor | response_agent
    graph.add_conditional_edges(
        "triage_agent",
        _route_after_triage,
        {
            "supervisor": "supervisor",
            "response_agent": "response_agent",
        },
    )

    # supervisor → SMALL_TALK: response_agent | DIABETES: fan-out (Send)
    graph.add_conditional_edges(
        "supervisor",
        _dispatch_sub_agents,
        ["factor_agent", "suggestion_agent", "harm_agent", "response_agent"],
    )

    # fan-in: all 3 sub-agents → aggregate
    graph.add_edge("factor_agent", "aggregate")
    graph.add_edge("suggestion_agent", "aggregate")
    graph.add_edge("harm_agent", "aggregate")

    # aggregate → response_agent → END
    graph.add_edge("aggregate", "response_agent")
    graph.add_edge("response_agent", END)

    logger.info("StateGraph built successfully (UC-012 Multi-Agent)")
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
