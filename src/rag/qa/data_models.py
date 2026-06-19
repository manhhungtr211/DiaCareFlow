from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Query:
    text: str
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not self.text or not self.text.strip():
            raise ValueError("Query text must not be empty")
        words = self.text.split()
        if len(words) > 500:
            raise ValueError("Query text exceeds 500 words")


@dataclass
class ChunkResult:
    content: str
    source: str
    score: float


@dataclass
class RetrievedContext:
    chunks: list[ChunkResult]
    query_vector: list[float]


@dataclass
class Answer:
    text: str
    sources: list[ChunkResult] = field(default_factory=list)
    is_refused: bool = False
    refuse_reason: str | None = None


@dataclass
class GuardrailResult:
    is_safe: bool
    reason: str | None = None
