import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
import pytest
from src.rag.qa.data_models import Query

import logging

logger = logging.getLogger(__name__)
EMBEDDING_MODEL = "keepitreal/vietnamese-sbert"
COLLECTION_NAME="medical_documents"
QDRANT_URL="http://localhost:6333"
def retrieve(query: Query, top_k: int = 3, score_threshold: float = 0.3):
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
        return None

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
            chunk = hit.payload.get("content", "")
            chunks.append(chunk)
            
        logger.info(f"Retrieved {len(chunks)} chunks.")
        return chunks

    except Exception as e:
        logger.error(f"Failed to query Qdrant: {e}")
        return None

def test_retriever_returns_chunks():
    query = Query(text="bệnh tiểu đường là gì")
    result = retrieve(query, top_k=3)
    print(result)

if __name__ == "__main__":
    test_retriever_returns_chunks()
