# Implementation Plan: UC-003 — Nạp Tài liệu Y khoa vào Hệ thống RAG

**Branch**: `001-diabetes-support-agents` | **Date**: 2026-06-15 | **Spec**: [UC-003-nap-tai-lieu-rag.md](../use-cases/UC-003-nap-tai-lieu-rag.md)

**Input**: Feature specification from `specs/use-cases/UC-003-nap-tai-lieu-rag.md`

## Summary

Xây dựng pipeline nạp tài liệu PDF y khoa tiếng Việt vào hệ thống RAG. 
Pipeline bao gồm: đọc PDF → chunking → embedding → lưu vào Qdrant. Chạy dưới dạng CLI script (batch, một lần) phục vụ MVP Tuần 1. Sử dụng Python 3.12 với PyMuPDF (đọc PDF), LangChain text splitters (chunking), và Qdrant client (lưu trữ vector), sử dụng Google API để embedding và sinh câu trả lời.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**:
- `pymupdf` (fitz) — Đọc nội dung text từ PDF, hỗ trợ tốt tiếng Việt
- `langchain-text-splitters` — Chia nhỏ nội dung thành chunks (RecursiveCharacterTextSplitter)
- `qdrant-client` — Python client cho Qdrant vector database
- `langchain-google-genai` — Google Generative AI Embeddings (model `models/embedding-001` hoặc `models/text-embedding-004`)
- `python-dotenv` — Quản lý biến môi trường (API keys)

**Storage**: Qdrant (Vector Database), chạy local qua Docker trên port 6333

**Testing**: pytest + kiểm tra thủ công qua CLI

**Target Platform**: Local / Docker (Windows development)

**Project Type**: CLI script (batch processing)

**Performance Goals**: Nạp xong 1 file PDF ~50 trang trong dưới 5 phút

**Constraints**: Chỉ hỗ trợ PDF có text (không OCR), tài liệu tiếng Việt, MVP không cần real-time

**Scale/Scope**: 1 file PDF mẫu (~36MB: `BMC_Diabetes_Handout_2024_vie.pdf`), mở rộng cho nhiều file sau

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution chưa được cấu hình cụ thể cho project (template mặc định). Không có gate violations. Tiến hành Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-diabetes-support-agents/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
src/
├── ingestion/
│   ├── __init__.py
│   ├── pdf_reader.py        # Đọc nội dung text từ PDF (PyMuPDF)
│   ├── chunker.py           # Chia nhỏ text thành chunks
│   ├── embedding.py          # Tạo embedding vectors
│   ├── qdrant_store.py      # Lưu trữ chunks + embeddings vào Qdrant
│   └── pipeline.py          # Orchestrate toàn bộ pipeline
├── config.py                # Cấu hình chung (chunk size, collection name, etc.)
└── cli.py                   # CLI entry point

tests/
├── unit/
│   ├── test_pdf_reader.py
│   ├── test_chunker.py
│   └── test_qdrant_store.py
└── integration/
    └── test_pipeline.py

data/
└── raw_data/
    └── BMC_Diabetes_Handout_2024_vie.pdf   # Tài liệu mẫu (đã có sẵn)
```

**Structure Decision**: Single project layout (Option 1 — CLI script). Thư mục `src/ingestion/` chứa toàn bộ logic pipeline. `cli.py` là entry point chạy qua Terminal.

