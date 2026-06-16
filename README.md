# DiaCareFlow
# BR-001: DiaCareFlow — Hỗ trợ bệnh tiểu đường 
## Goal 
- Hệ thống multi-agent Intelligent hỗ trợ bệnh tiểu đường cá nhân hóa
- Tìm kiếm RAG và truy xuất thông tin Web Search để cung cấp thông tin giáo dục sức khỏe dựa trên bằng chứng y khoa cục bộ và tìm kiểm trên web theo thời gian thực
- Tích hợp pipeline xử lý tài liệu (Parse PDF, tạo metadata, chia nhỏ tài liệu và tải lên Vector DB) cho phép người dùng bổ sung kiến thức riêng vào hệ thống.
- AI dự kiến: Supervisor Agent, Suggestion Agent, Harm Assessment Agent, Factor Analysis Agent, Response Agent.

- Hệ thống User: làm tính năng Đăng nhập/Đăng ký,lưu trữ lịch sử chat của người dùng.
- Tích hợp API End-to-End: nối luồng giao tiếp giữa Frontend và Backend 
- Deployment: triển khai (deploy) lên Cloud (AWS/GCP)
 
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
