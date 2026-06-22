from __future__ import annotations
import logging

from src.rag.qa.data_models import Answer, Query
from src.rag.qa.guardrail import check_guardrail
from src.rag.qa.retriever import retrieve
from src.rag.qa.generator import generate

logger = logging.getLogger(__name__)

def ask(question_text: str, top_k) -> Answer:
    """
    Main Q&A pipeline:
    1. Validate and check guardrail
    2. Retrieve context from Qdrant
    3. Generate answer using LLM
    """
    logger.info(f"Received question: '{question_text}'")

    try:
        # 0. Validate query
        try:
            query = Query(text=question_text)
        except ValueError as e:
            return Answer(
                text="",
                is_refused=True,
                refuse_reason=str(e)
            )

        # 1. Guardrail
        guard_result = check_guardrail(query)
        if not guard_result.is_safe:
            logger.info(f"Question refused by guardrail: {guard_result.reason}")
            return Answer(
                text="",
                is_refused=True,
                refuse_reason=guard_result.reason
            )
            
        # 2. Retrieve
        context = retrieve(query, top_k=top_k)
        
        # 3. Generate
        answer = generate(query, context)
        
        return answer
        
    except Exception as e:
        logger.exception("Unexpected error in Q&A pipeline")
        return Answer(
            text="Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau.",
            is_refused=False
        )
