"""
Document chunking module using LangChain text splitters.

Splits extracted text into smaller chunks suitable for RAG retrieval.
"""

from __future__ import annotations

import logging
import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import CHUNK_OVERLAP, CHUNK_SIZE
from src.rag.ingestion.data_models import DocumentChunk, SourceDocument

logger = logging.getLogger(__name__)


def chunk_document(
    document: SourceDocument,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[DocumentChunk]:
    """Split a SourceDocument into smaller DocumentChunks.

    Uses RecursiveCharacterTextSplitter which prioritizes splitting at
    paragraph and sentence boundaries, preserving context better than
    fixed-size splitting.

    Args:
        document: The source document to split.
        chunk_size: Maximum chunk size in characters (defaults to config).
        chunk_overlap: Overlap between chunks in characters (defaults to config).

    Returns:
        List of DocumentChunk objects with metadata.
    """
    size = chunk_size or CHUNK_SIZE
    overlap = chunk_overlap or CHUNK_OVERLAP

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    # Split the full document content
    texts = splitter.split_text(document.content)

    # Generate a shared document_id for all chunks from this document
    document_id = str(uuid.uuid4())

    chunks: list[DocumentChunk] = []
    for idx, text in enumerate(texts):
        # Estimate page number based on position in original content
        # Find where this chunk starts in the original content
        chunk_start = document.content.find(text[:50]) if len(text) >= 50 else document.content.find(text)
        page = _estimate_page(document.content, chunk_start, document.total_pages)

        chunk = DocumentChunk(
            document_id=document_id,
            content=text,
            source=document.file_name,
            page=page,
            chunk_index=idx,
        )
        chunks.append(chunk)

    logger.info(
        "Split '%s' into %d chunks (size=%d, overlap=%d).",
        document.file_name,
        len(chunks),
        size,
        overlap,
    )

    return chunks


def _estimate_page(full_text: str, char_position: int, total_pages: int) -> int:
    """Estimate which page a character position belongs to.

    Uses a simple proportional estimation based on character position
    relative to total text length.

    Args:
        full_text: The complete document text.
        char_position: Character position of the chunk start.
        total_pages: Total number of pages in the document.

    Returns:
        Estimated 1-based page number.
    """
    if char_position < 0 or not full_text:
        return 1

    proportion = char_position / len(full_text)
    page = int(proportion * total_pages) + 1
    return min(page, total_pages)
