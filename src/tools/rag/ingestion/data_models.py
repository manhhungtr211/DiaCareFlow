from __future__ import annotations
import os
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceDocument:
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
    file_name: str
    error_type: str
    message: str


@dataclass
class IngestionResult:
    total_files: int = 0
    success_files: int = 0
    failed_files: int = 0
    total_chunks: int = 0
    elapsed_seconds: float = 0.0
    errors: list[IngestionError] = field(default_factory=list)
