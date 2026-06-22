# DiaCareFlow
# BR: DiaCareFlow — Hỗ trợ bệnh tiểu đường 
## Goal 
- Xây dựng hệ thống Intelligent Multi-Agent cá nhân hóa hỗ trợ bệnh tiểu đường, được điều phối bởi LangGraph và định dạng cấu trúc dữ liệu bằng PydanticAI.

- Sử dụng mô hình Gemini 2.0 Flash làm lõi xử lý ngôn ngữ tự nhiên.

- Tích hợp công cụ: Tìm kiếm RAG (truy xuất từ Vector Database Qdrant) và Web Search (SearXNG) theo thời gian thực để cung cấp thông tin giáo dục sức khỏe nội bộ và trực tuyến.  (có hiện thị nguồn lúc trả kết quả ở web, giống gemini google search)

- Tích hợp pipeline xử lý tài liệu (PDF parsing, chunking, tạo embeddings qua Google AI và nạp vào Qdrant) thông qua module doc_pipeline.

- AI Agents dự kiến: Supervisor Agent, Suggestion Agent, Harm Assessment Agent, Factor Analysis Agent, Response Agent.

- Hệ thống User: Xác thực bằng JWT, lưu trữ phiên trò chuyện (session/state của LangGraph) và lịch sử chat siêu tốc bằng Redis.

- Tích hợp API End-to-End: Xây dựng Backend bằng FastAPI, kết nối luồng giao tiếp với Frontend (Next.js) và hỗ trợ trả kết quả Real-time Streaming (truyền phát luồng JSON trạng thái tác tử và nội dung).

- Deployment: Triển khai lên Cloud (AWS/GCP) qua Docker.
 
## Success Metrics
- Kỹ thuật: Real-time Streaming. RAG phải truy xuất tài liệu y khoa đạt trên 90%
- Chỉ số an toàn: Phát hiện 100% các truy vấn nguy hiểm và đưa ra cảnh báo. Không kê đơn thuốc, không chẩn đoán bệnh

## In Scope 
- RAG PoC: Chạy script nạp PDF (Tiền tiểu đường) vào Qdrant và test độ chính xác truy xuất nội dung.
- Agent Testing: Viết Prompt y khoa cho 5 Agents; test logic và output của từng node LangGraph riêng biệt.
- Safety Guardrails: Chạy test case giả lập để kiểm chứng khả năng chặn 100% các truy vấn kê đơn hoặc cấp cứu.
- Static UI: Chỉnh sửa giao diện tĩnh (Next.js) sang branding y tế, chưa cần nối luồng API Backend.
 
## Out of Scope 
- Cá nhân hóa các đề xuất cải thiện lối sống để ngăn ngừa bệnh tiến triển (idea sau)

---

## Quick Start: Nạp Tài liệu Y khoa (UC-003)

### Prerequisites

- **Python 3.12+**
- **Docker** (để chạy Qdrant)
- **Google AI API Key** (để tạo embeddings)

### 1. Khởi động Qdrant

```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

Kiểm tra: truy cập http://localhost:6333/dashboard

### 2. Cài đặt dependencies

```bash
uv pip install -r requirements.txt
```

### 3. Cấu hình

Tạo file `.env` tại thư mục gốc project (copy từ `.env.example`):

```bash
cp .env.example .env
# Sửa GOOGLE_API_KEY trong .env
```

### 4. Chạy nạp tài liệu

**Nạp một file PDF:**
```bash
python -m src.cli ingest data/raw_data/BMC_Diabetes_Handout_2024_vie.pdf
```

**Nạp tất cả PDF trong thư mục:**
```bash
python -m src.cli ingest data/raw_data/
```

**Tuỳ chọn nâng cao:**
```bash
python -m src.cli ingest data/raw_data/ \
  --collection medical_documents \
  --chunk-size 1000 \
  --chunk-overlap 200 \
  --qdrant-url http://localhost:6333
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0`  | Tất cả files nạp thành công |
| `1`  | Một hoặc nhiều files bị lỗi |
| `2`  | Lỗi hệ thống (Qdrant unreachable, etc.) |

### Project Structure

```
src/
├── cli.py                    # CLI entry point
├── config.py                 # Configuration (loads .env)
└── ingestion/
    ├── models.py             # Data models (SourceDocument, DocumentChunk, etc.)
    ├── pdf_reader.py         # PDF text extraction (PyMuPDF)
    ├── chunker.py            # Text chunking (RecursiveCharacterTextSplitter)
    ├── embedding.py          # Embedding generation (Google AI)
    ├── qdrant_store.py       # Qdrant vector storage
    └── pipeline.py           # Pipeline orchestrator
```
