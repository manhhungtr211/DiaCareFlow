from __future__ import annotations
import logging

from src.tools.rag.qa.data_models import Answer, Query
from src.tools.rag.qa.guardrail import check_guardrail
from src.tools.rag.qa.retriever import retrieve
from src.tools.rag.qa.generator import generate

logger = logging.getLogger(__name__)

def ask(question_text: str) -> Answer:
    """
    Main Q&A pipeline — delegates to LangGraph Multi-Agent pipeline.
    """
    logger.info(f"Delegating to LangGraph pipeline: '{question_text}'")
    from src.agents.pipeline import ask_langgraph
    return ask_langgraph(question_text)

