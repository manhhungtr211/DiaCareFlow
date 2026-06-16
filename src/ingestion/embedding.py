"""
Embedding module using Google Generative AI Embeddings.

Generates embedding vectors for document chunks using the
text-embedding-004 model via langchain-google-genai.
"""

from __future__ import annotations

import logging
import uuid

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.config import EMBEDDING_MODEL, GOOGLE_API_KEY
from src.ingestion.data_models import DocumentChunk, EmbeddedChunk

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""

    pass


def _get_embedding_model(
    api_key: str | None = None,
    model: str | None = None,
) -> GoogleGenerativeAIEmbeddings:
    """Create a Google Generative AI Embeddings instance.

    Args:
        api_key: Google API key (defaults to config).
        model: Embedding model name (defaults to config).

    Returns:
        Configured GoogleGenerativeAIEmbeddings instance.

    Raises:
        EmbeddingError: If API key is not configured.
    """
    key = api_key or GOOGLE_API_KEY
    mdl = model or EMBEDDING_MODEL

    if not key:
        raise EmbeddingError(
            "GOOGLE_API_KEY is not set. Please configure it in .env file."
        )

    return GoogleGenerativeAIEmbeddings(
        model=mdl,
        google_api_key=key,
    )


def embed_chunks(
    chunks: list[DocumentChunk],
    api_key: str | None = None,
    model: str | None = None,
) -> list[EmbeddedChunk]:
    """Generate embedding vectors for a list of document chunks.

    Uses Google Generative AI Embeddings (text-embedding-004) to create
    768-dimensional vectors for each chunk's text content.

    Args:
        chunks: List of DocumentChunk objects to embed.
        api_key: Google API key override.
        model: Embedding model override.

    Returns:
        List of EmbeddedChunk objects with vectors and payloads.

    Raises:
        EmbeddingError: If embedding generation fails.
    """
    if not chunks:
        return []

    embeddings_model = _get_embedding_model(api_key, model)

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
