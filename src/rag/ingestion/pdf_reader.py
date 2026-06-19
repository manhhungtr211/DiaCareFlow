"""
PDF reader module using PyMuPDF (fitz).

Extracts text content from PDF files, supporting Vietnamese text.
"""

from __future__ import annotations

import logging
import os

import fitz  # PyMuPDF

from src.rag.ingestion.data_models import SourceDocument

logger = logging.getLogger(__name__)


class PDFReadError(Exception):
    """Raised when a PDF file cannot be read or contains no extractable text."""

    pass


def read_pdf(file_path: str) -> SourceDocument:
    """Read text content from a PDF file using PyMuPDF.

    Args:
        file_path: Path to the PDF file.

    Returns:
        SourceDocument with extracted text and metadata.

    Raises:
        FileNotFoundError: If the file does not exist.
        PDFReadError: If the file cannot be read or has no text content.
    """
    # Validate file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    abs_path = os.path.abspath(file_path)
    file_name = os.path.basename(abs_path)

    if not file_name.lower().endswith(".pdf"):
        raise PDFReadError(f"Not a PDF file: {file_name}")

    file_size = os.path.getsize(abs_path)

    logger.info("Reading PDF: %s (%d bytes)", file_name, file_size)

    try:
        doc = fitz.open(abs_path)
    except Exception as e:
        raise PDFReadError(
            f"Cannot open PDF file '{file_name}': {e}"
        ) from e

    total_pages = len(doc)
    if total_pages == 0:
        doc.close()
        raise PDFReadError(f"PDF file '{file_name}' has 0 pages")

    # Extract text from all pages
    pages_text: list[str] = []
    for page_num in range(total_pages):
        page = doc[page_num]
        text = page.get_text("text")
        if text and text.strip():
            pages_text.append(text)

    doc.close()

    # Join all page text
    content = "\n\n".join(pages_text)

    if not content.strip():
        raise PDFReadError(
            f"PDF file '{file_name}' contains no extractable text "
            "(possibly scanned/image-only PDF)"
        )

    logger.info(
        "Extracted %d pages, %d characters from '%s'.",
        total_pages,
        len(content),
        file_name,
    )

    return SourceDocument(
        file_name=file_name,
        content=content,
        total_pages=total_pages,
        file_size=file_size,
    )
