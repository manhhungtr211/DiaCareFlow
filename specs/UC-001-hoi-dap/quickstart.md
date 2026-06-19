# Quickstart: UC-001 — Hỏi đáp Y khoa về Tiểu đường

## Prerequisites

1. Python 3.12+ đã cài đặt
2. Qdrant đang chạy tại `http://localhost:6333`
3. Collection `medical_documents` đã có dữ liệu (chạy UC-003 trước)
4. File `.env` đã cấu hình `GOOGLE_API_KEY`
5. Dependencies đã cài: `pip install -r requirements.txt`

## Chạy thử

### 1. Khởi động Qdrant (nếu chưa chạy)

```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 2. Chạy CLI hỏi đáp

```bash
python -m src.cli ask
```

Hệ thống sẽ hiển thị prompt, nhập câu hỏi:

```
🤖 DiaCareFlow — Hỏi đáp Y khoa về Tiểu đường
Gõ câu hỏi hoặc 'quit' để thoát.

> Tiền tiểu đường là gì?
```

### 3. Kết quả mong đợi

**Câu hỏi hợp lệ** — Trả về câu trả lời từ tài liệu:
```
> Tiền tiểu đường là gì?

📋 Câu trả lời:
Tiền tiểu đường là tình trạng đường huyết cao hơn mức bình thường...

📎 Nguồn: BMC_Diabetes_Handout_2024_vie.pdf (trang 3, 5)
```

**Câu hỏi ngoài phạm vi** — Từ chối thân thiện:
```
> Thời tiết hôm nay thế nào?

⚠️ Xin lỗi, tôi chỉ hỗ trợ câu hỏi về tiểu đường.
```

**Không tìm thấy thông tin** — Thông báo trung thực:
```
> Phẫu thuật dạ dày có chữa được tiểu đường không?

📋 Câu trả lời:
Tôi không tìm thấy thông tin về chủ đề này trong tài liệu hiện có.
```

## Kiểm tra thủ công

Chạy bộ test câu hỏi mẫu:

```bash
pytest tests/integration/test_qa_pipeline.py -v
```
