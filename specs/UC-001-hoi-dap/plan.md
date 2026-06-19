# Implementation Plan: UC-001 — Hỏi đáp Y khoa về Tiểu đường

**Date**: 2026-06-19 | **Spec**: [UC-001-hoi-dap-tieu-duong.md](../use-cases/UC-001-hoi-dap-tieu-duong.md)

**Input**: Feature specification from `specs/use-cases/UC-001-hoi-dap-tieu-duong.md`


**Tái sử dụng từ UC-003** (đã có sẵn):
- Qdrant server (Docker, port 6333) + collection `medical_documents`
- Embedding model: `keepitreal/vietnamese-sbert` via `HuggingFaceEmbeddings`
- Config: `src/config.py` (QDRANT_URL, COLLECTION_NAME, EMBEDDING_MODEL, VECTOR_SIZE)
- Data models: `src/ingestion/data_models.py`

**Dependencies mới**:
- `langchain-google-genai` — Đã có trong `requirements.txt`, dùng Gemini API để sinh câu trả lời

**Target Platform**: CLI (Terminal), local/Docker

---

## Project Structure

### Source Code mới cho UC-001

```text
src/
├── rag/
     ├── qa/                          # [NEW] Module hỏi đáp
     │   ├── __init__.py
     │   ├── guardrail.py             # Kiểm tra câu hỏi an toàn
     │   ├── retriever.py             # Truy xuất top-k chunks từ Qdrant
     │   ├── generator.py             # Sinh câu trả lời bằng LLM (Gemini)
     │   ├── pipeline.py              # Orchestrate: guardrail → retrieve → generate
     │   └── data_models.py           # Dataclasses cho Q&A (Query, Answer, etc.)
├── config.py                    # [MODIFY] Thêm config cho LLM model name
└── cli.py                       # [MODIFY] Thêm command `ask`

tests/
├── unit/
│   ├── test_guardrail.py        # [NEW]
│   ├── test_retriever.py        # [NEW]
│   └── test_generator.py        # [NEW]
└── integration/
    └── test_qa_pipeline.py      # [NEW]
```

---

## Luồng xử lý (Flow)

```
User Input (CLI)
     │
     ▼
┌─────────────┐
│  Validate   │──→ Input rỗng/quá dài? → Báo lỗi thân thiện
└─────────────┘
     │
     ▼
┌─────────────┐
│  Guardrail  │──→ Không liên quan tiểu đường? → Từ chối
└─────────────┘
     │ (safe)
     ▼
┌─────────────┐
│  Retrieve   │──→ Embed query → Qdrant search top-3
└─────────────┘
     │
     ▼
┌─────────────┐
│  Generate   │──→ Prompt + context → Gemini → Answer
└─────────────┘
     │
     ▼
  Output (CLI)
```

---

## Chi tiết từng module

### 1. `src/qa/data_models.py` — Data models

Định nghĩa dataclasses: `Query`, `ChunkResult`, `RetrievedContext`, `GuardrailResult`, `Answer`.

Xem chi tiết tại [data-model.md](data-model.md).

---

### 2. `src/qa/guardrail.py` — Kiểm tra an toàn

**Chức năng**: Lọc câu hỏi trước khi xử lý.

**Logic**:
- Kiểm tra input rỗng hoặc chỉ chứa ký tự đặc biệt → trả `GuardrailResult(is_safe=False, reason="...")`
- Kiểm tra input >500 từ → yêu cầu rút gọn
- Dùng LLM (Gemini) phân loại nhanh: "Câu hỏi này có liên quan đến tiểu đường/y tế không?" → Yes/No
  - Nếu No → `is_safe=False` với thông báo chỉ hỗ trợ về tiểu đường

---

### 3. `src/qa/retriever.py` — Truy xuất tài liệu

**Chức năng**: Tìm top-k chunks liên quan nhất từ Qdrant.

**Logic**:
1. Tạo embedding vector cho câu hỏi (cùng model `vietnamese-sbert` đã dùng khi nạp)
2. Query Qdrant collection `medical_documents` với `search()`, lấy top-5, score threshold ≥ 0.3
3. Trả về `RetrievedContext` chứa danh sách `ChunkResult`

**Tái sử dụng**: `src/config.py` (QDRANT_URL, COLLECTION_NAME, EMBEDDING_MODEL), `qdrant_store.get_client()`

---

### 4. `src/qa/generator.py` — Sinh câu trả lời

**Chức năng**: Gọi LLM tổng hợp câu trả lời từ context.

**Logic**:
1. Xây dựng prompt:
   - System: "Bạn là trợ lý y tế. Chỉ trả lời dựa trên tài liệu được cung cấp. Nếu không tìm thấy thông tin, nói rõ."
   - User: câu hỏi + context (nối các chunks)
2. Gọi Gemini API (`gemini-2.0-flash`) qua `langchain-google-genai`
3. Nếu context rỗng (không có chunk nào score ≥ threshold) → trả lời "không tìm thấy thông tin"
4. Trả về `Answer` kèm sources

---

### 5. `src/qa/pipeline.py` — Orchestrate

**Chức năng**: Kết nối guardrail → retriever → generator.

```python
def ask(question: str) -> Answer:
    # 1. Validate & Guardrail
    guard_result = check_guardrail(question)
    if not guard_result.is_safe:
        return Answer(text="", is_refused=True, refuse_reason=guard_result.reason)
    
    # 2. Retrieve
    context = retrieve(question, top_k=5)
    
    # 3. Generate
    answer = generate(question, context)
    return answer
```

---

### 6. `src/cli.py` — Thêm command `ask`

**Thay đổi**: Thêm subcommand `ask` vào CLI hiện tại.

```bash
python -m src.cli ask
```

Interactive loop: nhận câu hỏi → gọi `pipeline.ask()` → in kết quả → lặp lại cho đến khi gõ `quit`.

---

## Verification Plan

### Unit Tests
```bash
pytest tests/unit/test_guardrail.py tests/unit/test_retriever.py tests/unit/test_generator.py -v
```

### Integration Test
```bash
# Yêu cầu Qdrant đang chạy + có dữ liệu
pytest tests/integration/test_qa_pipeline.py -v
```

### Manual Verification
- Chạy `python -m src.cli ask` và thử các câu hỏi trong [quickstart.md](quickstart.md)
- Kiểm tra 3 acceptance criteria từ spec:
  1. Hỏi "Tiền tiểu đường là gì?" → trả lời đúng
  2. Hỏi về dinh dưỡng → trả lời từ tài liệu
  3. Hỏi ngoài tài liệu → thông báo trung thực
