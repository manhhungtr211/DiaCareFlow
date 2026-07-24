"""
Integration test for the LangGraph Multi-Agent pipeline (UC-012 T026).

Verifies the end-to-end flow using ask_langgraph() with external dependencies
(ChatGroq, retrieve, web_search) mocked out.

Covers:
- AC-1: Happy Path (Triage -> Supervisor -> Sub-Agents -> Aggregate -> Response).
- AC-2: Unsafe Path (Triage -> Response, bypassing sub-agents).
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from src.agents.pipeline import ask_langgraph
from src.agents.state import SafetyCategory
from src.tools.rag.qa.data_models import Answer, GuardrailResult


def _make_mock_llm(content: str):
    """Helper to create a mocked LLM returning specific content."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content=content)
    return mock_llm


def _make_triage_mock_safe():
    """Mock triage output indicating SAFE."""
    return GuardrailResult(
        is_safe=True,
        reason="All good"
    )


def _make_triage_mock_unsafe():
    """Mock triage output indicating UNSAFE (EMERGENCY)."""
    return GuardrailResult(
        is_safe=False,
        reason="Đây là một tình huống cấp cứu."
    )


def _make_supervisor_mock_diabetes():
    """Mock supervisor LLM output indicating DIABETES intent with sub-agent tasks."""
    mock_llm = MagicMock()
    # Supervisor v2 outputs JSON
    json_output = '''
    {
        "intent": "DIABETES",
        "factor_task": "What causes diabetes?",
        "suggestion_task": "How to treat diabetes?",
        "harm_task": "What are the risks of diabetes?",
        "follow_up_question": "",
        "should_response": false
    }
    '''
    mock_llm.invoke.return_value = MagicMock(content=json_output)
    return mock_llm


@patch("src.agents.nodes.response_agent.ChatGroq")
@patch("src.agents.nodes.harm_agent.ChatGroq")
@patch("src.agents.nodes.suggestion_agent.ChatGroq")
@patch("src.agents.nodes.factor_agent.ChatGroq")
@patch("src.agents.nodes.supervisor.ChatGroq")
@patch("src.agents.nodes.triage_node.check_guardrail")
# Mock tools
@patch("src.agents.nodes.harm_agent.retrieve")
@patch("src.agents.nodes.harm_agent.asyncio.run")
@patch("src.agents.nodes.suggestion_agent.retrieve")
@patch("src.agents.nodes.suggestion_agent.asyncio.run")
@patch("src.agents.nodes.factor_agent.retrieve")
@patch("src.agents.nodes.factor_agent.asyncio.run")
class TestMultiAgentPipelineIntegration:

    def test_happy_path_end_to_end(
        self,
        mock_factor_web,
        mock_factor_retrieve,
        mock_suggestion_web,
        mock_suggestion_retrieve,
        mock_harm_web,
        mock_harm_retrieve,
        mock_triage_llm,
        mock_supervisor_llm,
        mock_factor_llm,
        mock_suggestion_llm,
        mock_harm_llm,
        mock_response_llm,
    ):
        """
        AC-1: Happy Path.
        User asks a safe question -> Triage passes -> Supervisor routes to 3 sub-agents
        -> Aggregate -> Response generates final answer.
        """
        # 1. Setup Mocks
        mock_triage_llm.return_value = _make_triage_mock_safe()
        mock_supervisor_llm.return_value = _make_supervisor_mock_diabetes()
        
        # Sub-agents return simple summaries
        mock_factor_llm.return_value = _make_mock_llm("Nguyên nhân A")
        mock_suggestion_llm.return_value = _make_mock_llm("Lời khuyên B")
        mock_harm_llm.return_value = _make_mock_llm("Nguy cơ C")
        
        # Response agent
        mock_response_llm.return_value = _make_mock_llm("Câu trả lời tổng hợp: A, B, C.")

        # Tool mocks to return empty context, so LLM is not called if strict, wait, 
        # let's mock retrieve to return some dummy context so sub-agents DO call LLM.
        mock_retrieved = MagicMock()
        mock_chunk = MagicMock(content="Dummy", source="Doc", score=0.9)
        mock_retrieved.chunks = [mock_chunk]
        
        mock_factor_retrieve.return_value = mock_retrieved
        mock_suggestion_retrieve.return_value = mock_retrieved
        mock_harm_retrieve.return_value = mock_retrieved

        # 2. Execute
        question = "Người tiền tiểu đường nên ăn gì?"
        answer = ask_langgraph(question, session_id="test_session_1")

        # 3. Assertions
        assert isinstance(answer, Answer)
        assert answer.is_refused is False
        assert answer.text == "Câu trả lời tổng hợp: A, B, C."
        
        # Ensure all sub-agent LLMs were invoked
        assert mock_factor_llm.return_value.invoke.call_count == 1
        assert mock_suggestion_llm.return_value.invoke.call_count == 1
        assert mock_harm_llm.return_value.invoke.call_count == 1
        assert mock_response_llm.return_value.invoke.call_count == 1

    def test_unsafe_path_end_to_end(
        self,
        mock_factor_web,
        mock_factor_retrieve,
        mock_suggestion_web,
        mock_suggestion_retrieve,
        mock_harm_web,
        mock_harm_retrieve,
        mock_triage_llm,
        mock_supervisor_llm,
        mock_factor_llm,
        mock_suggestion_llm,
        mock_harm_llm,
        mock_response_llm,
    ):
        """
        AC-2: Unsafe Path.
        User asks an unsafe question -> Triage blocks it -> routes directly to Response
        -> Sub-agents are completely bypassed.
        """
        # 1. Setup Mocks
        mock_triage_llm.return_value = _make_triage_mock_unsafe()
        
        # Response agent should generate a refusal message
        mock_response_llm.return_value = _make_mock_llm("Tôi không thể tư vấn cấp cứu.")

        # 2. Execute
        question = "Tôi bị hạ đường huyết nặng, phải làm sao?"
        answer = ask_langgraph(question, session_id="test_session_2")

        # 3. Assertions
        assert isinstance(answer, Answer)
        assert "Tình huống khẩn cấp" in answer.text
        
        # Unsafe questions bypass all LLMs (except Triage which uses Guardrail here)
        assert mock_supervisor_llm.return_value.invoke.call_count == 0
        assert mock_factor_llm.return_value.invoke.call_count == 0
        assert mock_suggestion_llm.return_value.invoke.call_count == 0
        assert mock_harm_llm.return_value.invoke.call_count == 0
        assert mock_response_llm.return_value.invoke.call_count == 0
