"""
Validation script for UC-003 implementation.
Run this after setting up .env and starting Qdrant Docker.

Usage:
    python scripts/validate_setup.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_imports():
    """Verify all modules can be imported."""
    print("=== Checking Imports ===")
    
    try:
        from src.ingestion.data_models import (
            SourceDocument, DocumentChunk, EmbeddedChunk,
            IngestionResult, IngestionError,
        )
        print("✅ data_models OK")
    except Exception as e:
        print(f"❌ models FAILED: {e}")
        return False
    
    try:
        from src.config import CHUNK_SIZE, CHUNK_OVERLAP, COLLECTION_NAME, VECTOR_SIZE
        print(f"✅ config OK: chunk_size={CHUNK_SIZE}, collection={COLLECTION_NAME}")
    except Exception as e:
        print(f"❌ config FAILED: {e}")
        return False
    
    try:
        from src.ingestion.pdf_reader import read_pdf, PDFReadError
        print("✅ pdf_reader OK")
    except Exception as e:
        print(f"❌ pdf_reader FAILED: {e}")
        return False
    
    try:
        from src.ingestion.chunker import chunk_document
        print("✅ chunker OK")
    except Exception as e:
        print(f"❌ chunker FAILED: {e}")
        return False
    
    try:
        from src.ingestion.embedding import embed_chunks, EmbeddingError
        print("✅ embedding OK")
    except Exception as e:
        print(f"❌ embedding FAILED: {e}")
        return False
    
    try:
        from src.ingestion.qdrant_store import create_collection, upsert_chunks, get_collection_info
        print("✅ qdrant_store OK")
    except Exception as e:
        print(f"❌ qdrant_store FAILED: {e}")
        return False
    
    try:
        from src.ingestion.pipeline import ingest_file, ingest_directory
        print("✅ pipeline OK")
    except Exception as e:
        print(f"❌ pipeline FAILED: {e}")
        return False
    
    print("\n✅ ALL IMPORTS OK")
    return True


def check_pdf_reader():
    """Test PDF reader with the sample file."""
    print("\n=== Testing PDF Reader ===")
    from src.ingestion.pdf_reader import read_pdf, PDFReadError
    
    pdf_path = "data/raw_data/BMC_Diabetes_Handout_2024_vie.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"⚠️ Sample PDF not found: {pdf_path}")
        return False
    
    try:
        doc = read_pdf(pdf_path)
        print(f"✅ Read PDF: {doc.file_name}")
        print(f"   Pages: {doc.total_pages}")
        print(f"   Content length: {len(doc.content)} chars")
        print(f"   Preview: {doc.content[:200]}...")
        return True
    except PDFReadError as e:
        print(f"❌ PDFReadError: {e}")
        return False


def check_chunker():
    """Test chunker with sample document."""
    print("\n=== Testing Chunker ===")
    from src.ingestion.pdf_reader import read_pdf
    from src.ingestion.chunker import chunk_document
    
    pdf_path = "data/raw_data/BMC_Diabetes_Handout_2024_vie.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"⚠️ Sample PDF not found: {pdf_path}")
        return False
    
    try:
        doc = read_pdf(pdf_path)
        chunks = chunk_document(doc)
        print(f"✅ Created {len(chunks)} chunks")
        if chunks:
            print(f"   First chunk (index={chunks[0].chunk_index}, page={chunks[0].page}):")
            print(f"   {chunks[0].content[:150]}...")
        return True
    except Exception as e:
        print(f"❌ Chunker error: {e}")
        return False


def check_fake_pdf():
    """Test error handling with a fake PDF."""
    print("\n=== Testing Error Handling (fake PDF) ===")
    from src.ingestion.pdf_reader import read_pdf, PDFReadError
    
    fake_path = "data/raw_data/fake_test.pdf"
    
    # Create a fake PDF
    try:
        with open(fake_path, "w") as f:
            f.write("not a pdf content")
    except Exception as e:
        print(f"⚠️ Cannot create fake PDF: {e}")
        return False
    
    try:
        read_pdf(fake_path)
        print("❌ Should have raised PDFReadError")
        return False
    except PDFReadError as e:
        print(f"✅ Correctly raised PDFReadError: {e}")
        return True
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        # Cleanup
        if os.path.exists(fake_path):
            os.remove(fake_path)


def main():
    print("=" * 50)
    print("UC-003 Implementation Validation")
    print("=" * 50)
    
    results = []
    
    results.append(("Imports", check_imports()))
    results.append(("PDF Reader", check_pdf_reader()))
    results.append(("Chunker", check_chunker()))
    results.append(("Error Handling", check_fake_pdf()))
    
    print("\n" + "=" * 50)
    print("RESULTS SUMMARY")
    print("=" * 50)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} — {name}")
    
    all_passed = all(r[1] for r in results)
    print(f"\nOverall: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'}")
    
    print("\n" + "=" * 50)
    print("NEXT STEPS (manual validation):")
    print("=" * 50)
    print("1. Start Qdrant Docker:")
    print("   docker run -d --name qdrant -p 6333:6333 qdrant/qdrant")
    print()
    print("2. Configure .env with your GOOGLE_API_KEY")
    print()
    print("3. Run the full pipeline:")
    print("   python -m src.cli ingest data/raw_data/BMC_Diabetes_Handout_2024_vie.pdf")
    print()
    print("4. Check Qdrant dashboard:")
    print("   http://localhost:6333/dashboard")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
