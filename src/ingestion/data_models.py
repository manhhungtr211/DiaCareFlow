"""
Data models for the medical document ingestion pipeline.

Defines: SourceDocument, DocumentChunk, EmbeddedChunk, IngestionResult, IngestionError
Based on data-model.md specification.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceDocument:
    """Represents a source PDF file loaded into the system.

    Attributes:
        file_name: Basename of the file (e.g. 'BMC_Diabetes_Handout_2024_vie.pdf').
        content: Extracted text content from the PDF.
        total_pages: Total number of pages in the PDF.
        file_size: File size in bytes.
    """

    file_name: str
    content: str
    total_pages: int
    file_size: int

    def __post_init__(self) -> None:
        if not self.file_name:
            raise ValueError("file_name must not be empty")
        if self.total_pages < 1:
            raise ValueError("total_pages must be >= 1")
        if self.file_size < 0:
            raise ValueError("file_size must be >= 0")


@dataclass
class DocumentChunk:
    """A chunk of text extracted from a document, the basic retrieval unit.

    Attributes:
        document_id: UUID string identifying the source document.
        content: Text content of this chunk.
        source: Name of the source PDF file.
        page: Page number containing this chunk (1-based).
        chunk_index: Zero-based index of this chunk within the document.
    """

    document_id: str
    content: str
    source: str
    page: int
    chunk_index: int

    def __post_init__(self) -> None:
        if not self.content or not self.content.strip():
            raise ValueError("content must not be empty")
        if self.page < 1:
            raise ValueError("page must be >= 1")
        if self.chunk_index < 0:
            raise ValueError("chunk_index must be >= 0")


@dataclass
class EmbeddedChunk:
    """A chunk with its embedding vector, ready for Qdrant storage.

    Attributes:
        id: UUID string for this chunk (matches document chunk).
        vector: Embedding vector (list of floats).
        payload: Metadata dict with content, source, page, chunk_index, document_id.
    """

    id: str
    vector: list[float]
    payload: dict[str, Any]

    def __post_init__(self) -> None:
        if not self.vector:
            raise ValueError("vector must not be empty")
        for i, v in enumerate(self.vector):
            if not isinstance(v, (int, float)):
                raise ValueError(f"vector[{i}] must be a number, got {type(v)}")
            if v != v:  # NaN check
                raise ValueError(f"vector[{i}] is NaN")
            if v == float("inf") or v == float("-inf"):
                raise ValueError(f"vector[{i}] is Inf")


@dataclass
class IngestionError:
    """Details of an error during file processing.

    Attributes:
        file_name: Name of the file that caused the error.
        error_type: Category (FileNotFound, PDFReadError, EmbeddingError, QdrantError).
        message: Detailed error description.
    """

    file_name: str
    error_type: str
    message: str


@dataclass
class IngestionResult:
    """Result of the data ingestion process.

    Attributes:
        total_files: Total number of PDF files processed.
        success_files: Number of files processed successfully.
        failed_files: Number of files that failed.
        total_chunks: Total number of chunks uploaded to Qdrant.
        elapsed_seconds: Processing time in seconds.
        errors: List of detailed errors.
    """

    total_files: int = 0
    success_files: int = 0
    failed_files: int = 0
    total_chunks: int = 0
    elapsed_seconds: float = 0.0
    errors: list[IngestionError] = field(default_factory=list)
