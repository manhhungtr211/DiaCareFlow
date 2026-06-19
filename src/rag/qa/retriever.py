from __future__ import annotations
import logging
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient

from src.config import EMBEDDING_MODEL, QDRANT_URL, COLLECTION_NAME
from src.rag.qa.data_models import ChunkResult, Query, RetrievedContext

logger = logging.getLogger(__name__)

def retrieve(query: Query, top_k: int = 3, score_threshold: float = 0.3) -> RetrievedContext:
    """Retrieve top-k relevant chunks from Qdrant for a given query."""
    
    # 1. Embed query
    logger.info(f"Embedding query using {EMBEDDING_MODEL}")
    try:
        embeddings_model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        query_vector = embeddings_model.embed_query(query.text)
    except Exception as e:
        logger.error(f"Failed to embed query: {e}")
        return RetrievedContext(chunks=[], query_vector=[])

    # 2. Query Qdrant
    logger.info(f"Querying Qdrant collection {COLLECTION_NAME}")
    try:
        client = QdrantClient(url=QDRANT_URL, timeout=30)
        search_result = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            score_threshold=score_threshold
        )
        
        chunks = []
        for hit in search_result.points:
            chunk = ChunkResult(
                content=hit.payload.get("content", ""),
                source=hit.payload.get("source", "Unknown"),
                score=hit.score
            )
            chunks.append(chunk)
            
        logger.info(f"Retrieved {len(chunks)} chunks.")
        return RetrievedContext(chunks=chunks, query_vector=query_vector)

    except Exception as e:
        logger.error(f"Failed to query Qdrant: {e}")
        return RetrievedContext(chunks=[], query_vector=query_vector)
