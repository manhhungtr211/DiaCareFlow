"""
Qdrant vector database storage module.

Manages collection creation and chunk upsert operations
for the medical_documents collection.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.config import COLLECTION_NAME, QDRANT_URL, VECTOR_SIZE

if TYPE_CHECKING:
    from src.rag.ingestion.data_models import EmbeddedChunk

logger = logging.getLogger(__name__)


def get_client() -> QdrantClient:
    """Create and return a Qdrant client instance."""
    return QdrantClient(url=QDRANT_URL, timeout=30)


def create_collection(
    collection_name: str | None = None,
    vector_size: int | None = None,
) -> None:
    """Create a Qdrant collection if it does not already exist.

    Args:
        collection_name: Name of the collection (defaults to config).
        vector_size: Dimension of vectors (defaults to config).
    """
    name = collection_name or COLLECTION_NAME
    size = vector_size or VECTOR_SIZE
    client = get_client()

    # Check if collection already exists
    collections = client.get_collections().collections
    existing_names = [c.name for c in collections]

    if name in existing_names:
        logger.info("Collection '%s' already exists, skipping creation.", name)
        return

    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(
            size=size,
            distance=Distance.COSINE,
        ),
    )
    logger.info(
        "Created collection '%s' with vector size %d, distance=Cosine.",
        name,
        size,
    )


def upsert_chunks(
    chunks: list[EmbeddedChunk],
    collection_name: str | None = None,
) -> int:
    """Upsert embedded chunks into a Qdrant collection.

    Args:
        chunks: List of EmbeddedChunk objects to upsert.
        collection_name: Target collection name (defaults to config).

    Returns:
        Number of points successfully upserted.
    """
    name = collection_name or COLLECTION_NAME
    client = get_client()

    points = [
        PointStruct(
            id=chunk.id,
            vector=chunk.vector,
            payload=chunk.payload,
        )
        for chunk in chunks
    ]

    # Upsert in batches of 100
    batch_size = 100
    total_upserted = 0

    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=name, points=batch)
        total_upserted += len(batch)
        logger.info(
            "Upserted batch %d/%d (%d points).",
            (i // batch_size) + 1,
            (len(points) + batch_size - 1) // batch_size,
            len(batch),
        )

    return total_upserted


def get_collection_info(
    collection_name: str | None = None
) -> dict:
    """Get information about a Qdrant collection.

    Args:
        collection_name: Collection to query (defaults to config).
        qdrant_url: Qdrant server URL (defaults to config).

    Returns:
        Dict with 'points_count' and 'status' keys.
    """
    name = collection_name or COLLECTION_NAME
    client = get_client()

    info = client.get_collection(collection_name=name)
    return {
        "points_count": info.points_count,
        "status": info.status.value if info.status else "unknown",
    }
