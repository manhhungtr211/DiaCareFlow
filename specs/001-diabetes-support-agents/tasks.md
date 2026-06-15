# Tasks: UC-003 — Nạp Tài liệu Y khoa vào Hệ thống RAG

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US1]**: Belongs to the single user story: Nạp tài liệu PDF
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Khởi tạo project, cài đặt dependencies, tạo cấu trúc thư mục

- [ ] T001 Tạo cấu trúc thư mục project theo plan.md: `src/ingestion/`, `tests/unit/`, `tests/integration/`
- [ ] T002 Tạo file `requirements.txt` với các dependencies: `pymupdf`, `langchain-text-splitters`, `qdrant-client`, `langchain-google-genai`, `python-dotenv`, `pytest`
- [ ] T003 [P] Tạo file `.env.example` với các biến môi trường mẫu: `GOOGLE_API_KEY`, `QDRANT_URL`, `QDRANT_COLLECTION`
- [ ] T004 [P] Tạo file `src/__init__.py` và `src/ingestion/__init__.py` (package init)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config module và Qdrant connection — PHẢI hoàn thành trước khi implement các module pipeline

**⚠️ CRITICAL**: Không thể bắt đầu implement pipeline nếu chưa có config và kết nối Qdrant

- [ ] T005 Implement config module tại `src/config.py` — load `.env`, định nghĩa các hằng số: `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`, `COLLECTION_NAME="medical_documents"`, `QDRANT_URL`, `GOOGLE_API_KEY`, `VECTOR_SIZE=768`
- [ ] T006 Implement Qdrant connection và collection setup tại `src/ingestion/qdrant_store.py` — hàm `create_collection()` tạo collection `medical_documents` với vector size 768, distance Cosine, payload schema theo data-model.md; hàm `upsert_chunks()` nhận list EmbeddedChunk và lưu vào Qdrant; hàm `get_collection_info()` trả về số lượng points hiện có

**Checkpoint**: Config load được `.env`, Qdrant collection `medical_documents` tạo được trên local Docker

---

## Phase 3: User Story 1 — Nạp tài liệu PDF vào hệ thống RAG (Priority: P1) 🎯 MVP

**Goal**: Người vận hành chạy script CLI nạp file PDF, hệ thống tự động đọc → chunk → embed → lưu Qdrant, in báo cáo kết quả

**Independent Test**: Chạy `python -m src.cli ingest data/raw_data/BMC_Diabetes_Handout_2024_vie.pdf` → kiểm tra Qdrant có points mới, nội dung chunk chứa text tiếng Việt đúng

### Implementation for User Story 1

- [ ] T007 [P] [US1] Implement PDF reader tại `src/ingestion/pdf_reader.py` — hàm `read_pdf(file_path: str) -> SourceDocument` sử dụng PyMuPDF để đọc text từ từng trang PDF, trả về SourceDocument (theo data-model.md) với file_path, file_name, content, total_pages, file_size. Raise `PDFReadError` nếu file không đọc được hoặc không có text
- [ ] T008 [P] [US1] Implement chunker tại `src/ingestion/chunker.py` — hàm `chunk_document(document: SourceDocument) -> list[DocumentChunk]` sử dụng RecursiveCharacterTextSplitter với chunk_size và chunk_overlap từ config. Mỗi DocumentChunk có document_id (UUID), content, source, page, chunk_index
- [ ] T009 [P] [US1] Implement embedding module tại `src/ingestion/embedding.py` — hàm `embed_chunks(chunks: list[DocumentChunk]) -> list[EmbeddedChunk]` sử dụng GoogleGenerativeAIEmbeddings (model text-embedding-004) để tạo vector cho từng chunk. Mỗi EmbeddedChunk có id, vector, payload (content, source, page, chunk_index, document_id)
- [ ] T010 [US1] Implement pipeline orchestrator tại `src/ingestion/pipeline.py` — hàm `ingest_file(file_path: str) -> IngestionResult` gọi tuần tự: pdf_reader → chunker → embedding → qdrant_store. Hàm `ingest_directory(dir_path: str) -> IngestionResult` xử lý nhiều file, skip file lỗi và tiếp tục. Trả về IngestionResult với total_files, success_files, failed_files, total_chunks, elapsed_seconds, errors
- [ ] T011 [US1] Implement CLI entry point tại `src/cli.py` — command `ingest` nhận tham số `path` (file hoặc thư mục), options `--collection`, `--chunk-size`, `--chunk-overlap`, `--qdrant-url` (theo contracts/cli-ingest.md). In báo cáo ra stdout theo format đã định nghĩa. Exit code: 0 (thành công), 1 (có file lỗi), 2 (lỗi hệ thống)
- [ ] T012 [US1] Implement data models (Pydantic/dataclass) tại `src/ingestion/models.py` — định nghĩa SourceDocument, DocumentChunk, EmbeddedChunk, IngestionResult, IngestionError theo data-model.md với validation rules

**Checkpoint**: Chạy `python -m src.cli ingest data/raw_data/BMC_Diabetes_Handout_2024_vie.pdf` thành công, Qdrant chứa chunks mới, báo cáo hiển thị trên Terminal

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Cải thiện chất lượng, error handling, và validation end-to-end

- [ ] T013 [P] Thêm logging (Python logging module) vào tất cả modules trong `src/ingestion/` — log INFO cho tiến trình, WARNING cho cảnh báo, ERROR cho lỗi
- [ ] T014 [P] Tạo file `README.md` hoặc cập nhật docs cho hướng dẫn sử dụng script nạp tài liệu (setup Qdrant Docker, cài deps, chạy CLI)
- [ ] T015 Chạy quickstart.md validation — thực hiện 4 scenarios: nạp file thành công, kiểm tra chunks, file lỗi, Qdrant offline. Xác nhận tất cả pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (T001, T002 complete) — BLOCKS all user story work
- **User Story 1 (Phase 3)**: Depends on Phase 2 (T005, T006 complete)
- **Polish (Phase 4)**: Depends on Phase 3 complete

### Within User Story 1

```
T007 (pdf_reader) ─┐
T008 (chunker)     ├─→ T010 (pipeline) ─→ T011 (cli)
T009 (embedding)   ┘
T012 (models) ─────────→ T007, T008, T009 đều phụ thuộc vào T012
```

**Corrected order**: T012 (models) → T007, T008, T009 (parallel) → T010 (pipeline) → T011 (cli)

### Parallel Opportunities

- **Phase 1**: T003 và T004 có thể chạy song song
- **Phase 3**: T007, T008, T009 có thể chạy song song (sau khi T012 hoàn thành, các module thao tác trên file riêng biệt)

---

## Parallel Example: User Story 1

```bash
# Step 1: Data models first (blocking)
Task: T012 — Implement data models tại src/ingestion/models.py

# Step 2: Launch all pipeline modules in parallel
Task: T007 — Implement PDF reader tại src/ingestion/pdf_reader.py
Task: T008 — Implement chunker tại src/ingestion/chunker.py
Task: T009 — Implement embedding tại src/ingestion/embedding.py

# Step 3: Orchestrator (depends on T007, T008, T009)
Task: T010 — Implement pipeline tại src/ingestion/pipeline.py

# Step 4: CLI entry point (depends on T010)
Task: T011 — Implement CLI tại src/cli.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T006)
3. Complete Phase 3: User Story 1 (T007–T012)
4. **STOP and VALIDATE**: Chạy `python -m src.cli ingest data/raw_data/BMC_Diabetes_Handout_2024_vie.pdf` và kiểm tra Qdrant
5. Nếu pass → UC-003 hoàn thành, sẵn sàng cho UC-001 (hỏi đáp RAG)

### Incremental Delivery

1. Setup + Foundational → Project skeleton ready
2. Data models (T012) → Type-safe foundation
3. Pipeline modules (T007–T009 parallel) → Core logic ready
4. Pipeline + CLI (T010–T011) → End-to-end runnable (MVP!)
5. Polish (T013–T015) → Production-quality

---

## Notes

- [P] tasks = different files, no dependencies
- [US1] = all tasks belong to the single user story: Nạp tài liệu PDF
- Verify Qdrant Docker running before Phase 2
- Commit after each task or logical group
- Stop at Phase 3 checkpoint to validate MVP independently
- UC-003 là prerequisite cho UC-001 (hỏi đáp) — phải hoàn thành trước
