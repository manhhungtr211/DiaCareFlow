"""
Application configuration for the ingestion pipeline.

Loads settings from .env file and provides configuration constants
used across all pipeline modules.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env", override=True)

# --- Chunking settings ---
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "2000"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "300"))

# --- Qdrant settings ---
QDRANT_URL: str = os.getenv("QDRANT_URL")
COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION")
VECTOR_SIZE: int = int(os.getenv("VECTOR_SIZE", "768"))

# --- Groq AI settings ---
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL")
GENERATIVE_MODEL: str = os.getenv("MODEL")
