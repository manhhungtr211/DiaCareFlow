# Tasks: UC-003 — Nạp Tài liệu Y khoa vào Hệ thống RAG

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US1]**: Belongs to the single user story: Nạp tài liệu PDF
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Khởi tạo project, cài đặt dependencies, tạo cấu trúc thư mục

- [X] T001 Tạo cấu trúc thư mục project theo plan.md: `src/ingestion/`, `tests/unit/`, `tests/integration/`
- [X] T002 Tạo file `requirements.txt` với các dependencies: `pymupdf`, `langchain-text-splitters`, `qdrant-client`, `langchain-google-genai`, `python-dotenv`, `pytest`
- [X] T003 [P] Tạo file `.env.example` với các biến môi trường mẫu: `GOOGLE_API_KEY`, `QDRANT_URL`, `QDRANT_COLLECTION`
- [X] T004 [P] Tạo file `src/__init__.py` và `src/ingestion/__init__.py` (package init)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config module và Qdrant connection — PHẢI hoàn thành trước khi implement các module pipeline

**⚠️ CRITICAL**: Không thể bắt đầu implement pipeline nếu chưa có config và kết nối Qdrant

- [X] T005 Implement config module tại `src/config.py` — load `.env`, định nghĩa các hằng số: `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`, `COLLECTION_NAME="medical_documents"`, `QDRANT_URL`, `GOOGLE_API_KEY`, `VECTOR_SIZE=768`
- [X] T006 Implement Qdrant connection và collection setup tại `src/ingestion/qdrant_store.py` — hàm `create_collection()` tạo collection `medical_documents` với vector size 768, distance Cosine, payload schema theo data-model.md; hàm `upsert_chunks()` nhận list EmbeddedChunk và lưu vào Qdrant; hàm `get_collection_info()` trả về số lượng points hiện có

**Checkpoint**: Config load được `.env`, Qdrant collection `medical_documents` tạo được trên local Docker

---

## Phase 3: User Story 1 — Nạp tài liệu PDF vào hệ thống RAG (Priority: P1) 🎯 MVP

**Goal**: Người vận hành chạy script CLI nạp file PDF, hệ thống tự động đọc → chunk → embed → lưu Qdrant, in báo cáo kết quả

**Independent Test**: Chạy `python -m src.cli ingest data/raw_data/BMC_Diabetes_Handout_2024_vie.pdf` → kiểm tra Qdrant có points mới, nội dung chunk chứa text tiếng Việt đúng

### Implementation for User Story 1

- [X] T007 [P] [US1] Implement PDF reader tại `src/ingestion/pdf_reader.py` — hàm `read_pdf(file_path: str) -> SourceDocument` sử dụng PyMuPDF để đọc text từ từng trang PDF, trả về SourceDocument (theo data-model.md) với file_path, file_name, content, total_pages, file_size. Raise `PDFReadError` nếu file không đọc được hoặc không có text
- [X] T008 [P] [US1] Implement chunker tại `src/ingestion/chunker.py` — hàm `chunk_document(document: SourceDocument) -> list[DocumentChunk]` sử dụng RecursiveCharacterTextSplitter với chunk_size và chunk_overlap từ config. Mỗi DocumentChunk có document_id (UUID), content, source, page, chunk_index
- [X] T009 [P] [US1] Implement embedding module tại `src/ingestion/embedding.py` — hàm `embed_chunks(chunks: list[DocumentChunk]) -> list[EmbeddedChunk]` sử dụng GoogleGenerativeAIEmbeddings (model text-embedding-004) để tạo vector cho từng chunk. Mỗi EmbeddedChunk có id, vector, payload (content, source, page, chunk_index, document_id)
- [X] T010 [US1] Implement pipeline orchestrator tại `src/ingestion/pipeline.py` — hàm `ingest_file(file_path: str) -> IngestionResult` gọi tuần tự: pdf_reader → chunker → embedding → qdrant_store. Hàm `ingest_directory(dir_path: str) -> IngestionResult` xử lý nhiều file, skip file lỗi và tiếp tục. Trả về IngestionResult với total_files, success_files, failed_files, total_chunks, elapsed_seconds, errors
- [X] T011 [US1] Implement CLI entry point tại `src/cli.py` — command `ingest` nhận tham số `path` (file hoặc thư mục), options `--collection`, `--chunk-size`, `--chunk-overlap`, `--qdrant-url` (theo contracts/cli-ingest.md). In báo cáo ra stdout theo format đã định nghĩa. Exit code: 0 (thành công), 1 (có file lỗi), 2 (lỗi hệ thống)
- [X] T012 [US1] Implement data models (Pydantic/dataclass) tại `src/ingestion/models.py` — định nghĩa SourceDocument, DocumentChunk, EmbeddedChunk, IngestionResult, IngestionError theo data-model.md với validation rules

**Checkpoint**: Chạy `python -m src.cli ingest data/raw_data/BMC_Diabetes_Handout_2024_vie.pdf` thành công, Qdrant chứa chunks mới, báo cáo hiển thị trên Terminal

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Cải thiện chất lượng, error handling, và validation end-to-end

- [X] T013 [P] Thêm logging (Python logging module) vào tất cả modules trong `src/ingestion/` — log INFO cho tiến trình, WARNING cho cảnh báo, ERROR cho lỗi
- [X] T014 [P] Tạo file `README.md` hoặc cập nhật docs cho hướng dẫn sử dụng script nạp tài liệu (setup Qdrant Docker, cài deps, chạy CLI)
- [X] T015 Chạy quickstart.md validation — thực hiện 4 scenarios: nạp file thành công, kiểm tra chunks, file lỗi, Qdrant offline. Xác nhận tất cả pass

---



## Notes

- [P] tasks = different files, no dependencies
- [US1] = all tasks belong to the single user story: Nạp tài liệu PDF
- Verify Qdrant Docker running before Phase 2
- Commit after each task or logical group
- Stop at Phase 3 checkpoint to validate MVP independently
- UC-003 là prerequisite cho UC-001 (hỏi đáp) — phải hoàn thành trước
