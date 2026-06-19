
from __future__ import annotations

import logging
import uuid

from langchain_huggingface import HuggingFaceEmbeddings

from src.config import EMBEDDING_MODEL
from src.rag.ingestion.data_models import DocumentChunk, EmbeddedChunk

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""

    pass

def embed_chunks(chunks: list[DocumentChunk]) -> list[EmbeddedChunk]:
    if not chunks:
        return []

    # Sử dụng trực tiếp model keepitreal/vietnamese-sbert từ HuggingFace 
    # thay vì lấy từ EMBEDDING_MODEL trong .env (đang chứa tên model của Google)
    print(f"Embedding mode: {EMBEDDING_MODEL}")
    embeddings_model = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

    # Extract text contents for batch embedding
    texts = [chunk.content for chunk in chunks]

    logger.info("Generating embeddings for %d chunks...", len(texts))

    try:
        vectors = embeddings_model.embed_documents(texts)
    except Exception as e:
        raise EmbeddingError(
            f"Failed to generate embeddings: {e}"
        ) from e

    # Build EmbeddedChunk objects
    embedded_chunks: list[EmbeddedChunk] = []
    for chunk, vector in zip(chunks, vectors):
        chunk_id = str(uuid.uuid4())

        embedded = EmbeddedChunk(
            id=chunk_id,
            vector=vector,
            payload={
                "content": chunk.content,
                "source": chunk.source,
                "page": chunk.page,
                "chunk_index": chunk.chunk_index,
                "document_id": chunk.document_id,
            },
        )
        embedded_chunks.append(embedded)

    logger.info(
        "Generated %d embeddings (vector dim=%d).",
        len(embedded_chunks),
        len(vectors[0]) if vectors else 0,
    )

    return embedded_chunks

