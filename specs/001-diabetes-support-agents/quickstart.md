# Quickstart: UC-003 — Nạp Tài liệu Y khoa vào Hệ thống RAG

**Date**: 2026-06-15

## Prerequisites

1. **Python 3.12** đã cài đặt
2. **Docker** đang chạy (để khởi động Qdrant)
3. **Google AI API Key** (để tạo embeddings)
4. File PDF mẫu đã có sẵn tại `data/raw_data/BMC_Diabetes_Handout_2024_vie.pdf`

## Setup

### 1. Khởi động Qdrant

```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

Kiểm tra: truy cập `http://localhost:6333/dashboard` → thấy Qdrant UI.

### 2. Cấu hình biến môi trường

Tạo file `.env` tại root project:

```env
GOOGLE_API_KEY=your_google_ai_api_key_here
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=medical_documents
```

### 3. Cài đặt dependencies

```bash
pip install pymupdf langchain-text-splitters qdrant-client langchain-google-genai python-dotenv
```

## Validation Scenarios

### Scenario 1: Nạp file PDF thành công

**Chạy:**
```bash
python -m src.cli ingest data/raw_data/BMC_Diabetes_Handout_2024_vie.pdf
```

**Expected:**
- Script in ra tiến trình xử lý (số trang, số chunks)
- Kết thúc với báo cáo: `Successful: 1`, `Total chunks: > 0`
- Exit code: `0`

**Verify trên Qdrant:**
```bash
curl http://localhost:6333/collections/medical_documents
```
→ Response chứa `"points_count"` > 0

### Scenario 2: Kiểm tra nội dung chunks trong Qdrant

**Chạy query mẫu** (sau khi nạp):
```python
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")
results = client.scroll(
    collection_name="medical_documents",
    limit=3,
    with_payload=True,
    with_vectors=False
)
for point in results[0]:
    print(f"[Chunk {point.payload['chunk_index']}] Page {point.payload['page']}")
    print(f"Source: {point.payload['source']}")
    print(f"Content: {point.payload['content'][:200]}...")
    print("---")
```

**Expected:**
- Hiển thị 3 chunks với metadata đầy đủ (`source`, `page`, `chunk_index`)
- `content` chứa text tiếng Việt hợp lệ (có dấu, đúng nội dung)

### Scenario 3: File PDF lỗi

**Tạo file lỗi và chạy:**
```bash
echo "not a pdf" > data/raw_data/fake.pdf
python -m src.cli ingest data/raw_data/fake.pdf
```

**Expected:**
- Script in ra thông báo lỗi rõ ràng: tên file + lý do lỗi
- Không nạp dữ liệu hỏng vào Qdrant
- Exit code: `1`

**Cleanup:**
```bash
del data\raw_data\fake.pdf
```

### Scenario 4: Qdrant chưa chạy

**Dừng Qdrant và chạy:**
```bash
docker stop qdrant
python -m src.cli ingest data/raw_data/BMC_Diabetes_Handout_2024_vie.pdf
```

**Expected:**
- Script báo lỗi kết nối Qdrant rõ ràng
- Exit code: `2`

**Khôi phục:**
```bash
docker start qdrant
```

## Tiêu chí đánh giá

Xem chi tiết tại [data-model.md](data-model.md) và [CLI contract](contracts/cli-ingest.md).

| Tiêu chí | Ngưỡng | Cách kiểm tra |
|----------|--------|---------------|
| Nạp PDF thành công | 100% files hợp lệ | Scenario 1 |
| Chunks chứa text đúng | Kiểm tra thủ công 3-5 chunks | Scenario 2 |
| Báo lỗi file hỏng | Không nạp dữ liệu rác | Scenario 3 |
| Xử lý Qdrant offline | Báo lỗi kết nối, không crash | Scenario 4 |
| Thời gian xử lý | < 5 phút cho ~50 trang | Scenario 1 (đo thời gian) |
