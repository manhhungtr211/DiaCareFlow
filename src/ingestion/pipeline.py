"""
Pipeline orchestrator for the medical document ingestion process.

Coordinates the full pipeline: PDF reading → chunking → embedding → Qdrant storage.
"""

from __future__ import annotations

import logging
import os
import time

from src.ingestion.chunker import chunk_document
from src.ingestion.embedding import EmbeddingError, embed_chunks
from src.ingestion.data_models import IngestionError, IngestionResult
from src.ingestion.pdf_reader import PDFReadError, read_pdf
from src.ingestion.qdrant_store import create_collection, upsert_chunks

logger = logging.getLogger(__name__)


def ingest_file(
    file_path: str,
    collection_name: str | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    qdrant_url: str | None = None,
) -> IngestionResult:
    """Ingest a single PDF file into the RAG system.

    Runs the full pipeline: read PDF → chunk → embed → store in Qdrant.

    Args:
        file_path: Path to the PDF file.
        collection_name: Qdrant collection name override.
        chunk_size: Chunk size override.
        chunk_overlap: Chunk overlap override.
        qdrant_url: Qdrant URL override.

    Returns:
        IngestionResult with processing statistics.
    """
    start_time = time.time()
    result = IngestionResult(total_files=1)
    file_name = os.path.basename(file_path)

    try:
        # Step 1: Ensure collection exists
        logger.info("Ensuring Qdrant collection exists...")
        create_collection(
            collection_name=collection_name,
            qdrant_url=qdrant_url,
        )

        # Step 2: Read PDF
        print(f"📄 Processing: {file_name}")
        document = read_pdf(file_path)
        logger.info("Read %d pages from '%s'.", document.total_pages, file_name)

        # Step 3: Chunk document
        chunks = chunk_document(
            document,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        logger.info("Created %d chunks from '%s'.", len(chunks), file_name)

        # Step 4: Generate embeddings
        embedded_chunks = embed_chunks(chunks)
        logger.info(
            "Generated %d embeddings for '%s'.", len(embedded_chunks), file_name
        )

        # Step 5: Store in Qdrant
        upserted = upsert_chunks(
            embedded_chunks,
            collection_name=collection_name,
            qdrant_url=qdrant_url,
        )
        logger.info("Upserted %d points to Qdrant for '%s'.", upserted, file_name)

        print(
            f"   Pages: {document.total_pages} | "
            f"Chunks: {len(chunks)} | "
            f"✅ Uploaded to Qdrant"
        )

        result.success_files = 1
        result.total_chunks = len(chunks)

    except FileNotFoundError as e:
        _handle_file_error(result, file_name, "FileNotFound", str(e))
    except PDFReadError as e:
        _handle_file_error(result, file_name, "PDFReadError", str(e))
    except EmbeddingError as e:
        _handle_file_error(result, file_name, "EmbeddingError", str(e))
    except Exception as e:
        _handle_file_error(result, file_name, "QdrantError", str(e))

    result.elapsed_seconds = round(time.time() - start_time, 1)
    return result


def ingest_directory(
    dir_path: str,
    collection_name: str | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    qdrant_url: str | None = None,
) -> IngestionResult:
    """Ingest all PDF files in a directory into the RAG system.

    Processes each PDF file independently. Skips files that fail and
    continues with the remaining files.

    Args:
        dir_path: Path to the directory containing PDF files.
        collection_name: Qdrant collection name override.
        chunk_size: Chunk size override.
        chunk_overlap: Chunk overlap override.
        qdrant_url: Qdrant URL override.

    Returns:
        IngestionResult with aggregated statistics.
    """
    start_time = time.time()

    if not os.path.isdir(dir_path):
        raise FileNotFoundError(f"Directory not found: {dir_path}")

    # Find all PDF files
    pdf_files = sorted(
        [
            os.path.join(dir_path, f)
            for f in os.listdir(dir_path)
            if f.lower().endswith(".pdf")
        ]
    )

    if not pdf_files:
        logger.warning("No PDF files found in '%s'.", dir_path)
        return IngestionResult(elapsed_seconds=round(time.time() - start_time, 1))

    # Ensure collection exists once before processing files
    try:
        create_collection(
            collection_name=collection_name,
            qdrant_url=qdrant_url,
        )
    except Exception as e:
        # If we can't even connect to Qdrant, fail immediately
        raise ConnectionError(
            f"Cannot connect to Qdrant: {e}"
        ) from e

    combined = IngestionResult(total_files=len(pdf_files))

    for pdf_path in pdf_files:
        file_result = ingest_file(
            pdf_path,
            collection_name=collection_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            qdrant_url=qdrant_url,
        )
        combined.success_files += file_result.success_files
        combined.failed_files += file_result.failed_files
        combined.total_chunks += file_result.total_chunks
        combined.errors.extend(file_result.errors)

    combined.elapsed_seconds = round(time.time() - start_time, 1)
    return combined


def _handle_file_error(
    result: IngestionResult,
    file_name: str,
    error_type: str,
    message: str,
) -> None:
    """Record a file processing error in the result."""
    print(f"   ❌ Error: {error_type} — {message}")
    logger.error("Error processing '%s': [%s] %s", file_name, error_type, message)
    result.failed_files = 1
    result.errors.append(
        IngestionError(
            file_name=file_name,
            error_type=error_type,
            message=message,
        )
    )
