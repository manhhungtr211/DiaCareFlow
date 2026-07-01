from __future__ import annotations
import logging
import httpx
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient

from src.config import QDRANT_URL, COLLECTION_NAME, JINA_API_KEY
from src.rag.qa.data_models import ChunkResult, Query, RetrievedContext

logger = logging.getLogger(__name__)

def retrieve(query: Query, top_k: int = 20, score_threshold: float = 0.3) -> RetrievedContext:
    """Retrieve top-k relevant chunks from Qdrant for a given query."""
    top_n = 3
    # 1. Embed query
    logger.info("Embedding query using BGE-M3")
    try:
        from FlagEmbedding import BGEM3FlagModel
        embeddings_model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)
        encoded_result = embeddings_model.encode(
            [query.text],
            batch_size=1,
            max_length=8192
        )
        query_vector = encoded_result['dense_vecs'][0].tolist()
    except Exception as e:
        logger.error(f"Failed to embed query: {e}")
        return RetrievedContext(chunks=[], query_vector=[])

    # 2. Query Qdrant
    logger.info(f"Stage 1: Querying Qdrant collection {COLLECTION_NAME} for top 20")
    try:
        client = QdrantClient(url=QDRANT_URL, timeout=30)
        search_result = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            score_threshold=score_threshold
        )
        
        initial_chunks = []
        for hit in search_result.points:
            chunk = ChunkResult(
                content=hit.payload.get("content", ""),
                source=hit.payload.get("source", "Unknown"),
                score=hit.score
            )
            initial_chunks.append(chunk)
            
        logger.info(f"Stage 1 retrieved {len(initial_chunks)} chunks.")
    except Exception as e:
        logger.error(f"Failed to query Qdrant: {e}")
        return RetrievedContext(chunks=[], query_vector=query_vector)

    if not initial_chunks or not JINA_API_KEY:
        logger.info("Skipping reranking. Returning Qdrant results directly.")
        return RetrievedContext(chunks=initial_chunks[:top_n], query_vector=query_vector)

    # 3. Rerank using Jina AI
    logger.info("Stage 2: Reranking chunks using Jina AI")
    try:
        url = "https://api.jina.ai/v1/rerank"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {JINA_API_KEY}"
        }
        data = {
            "model": "jina-reranker-v2-base-multilingual",
            "query": query.text,
            "documents": [c.content for c in initial_chunks],
            "top_n": top_n
        }
        response = httpx.post(url, headers=headers, json=data, timeout=15)
        response.raise_for_status()
        
        reranked_results = response.json().get("results", [])
        
        final_chunks = []
        for res in reranked_results:
            idx = res["index"]
            original_chunk = initial_chunks[idx]
            final_chunks.append(ChunkResult(
                content=original_chunk.content,
                source=original_chunk.source,
                score=res["relevance_score"]
            ))
            
        logger.info(f"Stage 2 returning {len(final_chunks)} reranked chunks.")
        return RetrievedContext(chunks=final_chunks, query_vector=query_vector)

    except Exception as e:
        logger.error(f"Failed to rerank with Jina API: {e}. Falling back to Qdrant results.")
        return RetrievedContext(chunks=initial_chunks[:top_k], query_vector=query_vector)
