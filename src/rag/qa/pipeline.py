from __future__ import annotations
import logging

from src.rag.qa.data_models import Answer, Query
from src.rag.qa.guardrail import check_guardrail
from src.rag.qa.retriever import retrieve
from src.rag.qa.generator import generate

logger = logging.getLogger(__name__)

def ask(question_text: str, top_k: int = 3) -> Answer:
    """
    Main Q&A pipeline — delegates to LangGraph Multi-Agent pipeline.

    Backward compatible: CLI and evaluation runner import this function
    without any changes needed.
    """
    logger.info(f"Delegating to LangGraph pipeline: '{question_text}'")
    from src.agents.pipeline import ask_langgraph
    return ask_langgraph(question_text, top_k=top_k)

