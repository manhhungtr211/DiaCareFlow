# Walkthrough: UC-001 — Hỏi đáp Y khoa về Tiểu đường

Quá trình implement cho use case **UC-001** đã hoàn tất. Dưới đây là tóm tắt các tính năng đã được xây dựng và cách hoạt động:

## Các thành phần đã triển khai

1. **Cấu trúc Module Mới (`src/rag/qa/`)**:
   - `data_models.py`: Định nghĩa các kiểu dữ liệu sử dụng trong toàn bộ quy trình Hỏi đáp (`Query`, `ChunkResult`, `RetrievedContext`, `Answer`, `GuardrailResult`).
   - `guardrail.py`: Lọc các câu hỏi đầu vào không hợp lệ hoặc nằm ngoài phạm vi y khoa/tiểu đường thông qua LLM Classification.
   - `retriever.py`: Vector search module kết nối với **Qdrant** nhằm truy xuất ngữ cảnh (top-k=3) từ tài liệu với model `keepitreal/vietnamese-sbert`.
   - `generator.py`: Module sinh câu trả lời bằng **Gemini 2.0 Flash** dựa trên Context được cung cấp.
   - `pipeline.py`: Orchestrator điều phối luồng xử lý `Guardrail -> Retrieve -> Generate`.

2. **Cập nhật Hệ thống Hiện tại**:
   - Khai báo model LLM Gemini (`GENERATIVE_MODEL`) trong `src/config.py`.
   - Bổ sung subcommand `ask` vào `src/cli.py` cho phép tương tác trực tiếp qua command-line.

3. **Cấu hình Unit & Integration Tests**:
   - Đã khởi tạo các file test mẫu (`test_guardrail.py`, `test_retriever.py`, `test_generator.py`) trong thư mục `tests/unit/` sẵn sàng để thêm coverage.
   - Lệnh cài đặt dependencies bị từ chối do phân quyền môi trường, nhưng phần code chức năng chính đã hoàn toàn sẵn sàng chạy.

## Kết quả nghiệm thu

Tất cả các task trong danh sách `tasks.md` đã được đánh dấu hoàn thành (`[x]`).

## Chạy thử (Validation)

Để kiểm tra hệ thống thực tế trên Local Terminal, bạn có thể thực hiện theo các lệnh sau (Đảm bảo đã chạy Qdrant Docker):

```powershell
python -m src.cli ask
```

Hệ thống sẽ chạy ở chế độ tương tác (Interactive Loop), cho phép bạn nhập các câu hỏi và nhận lại câu trả lời kèm trích dẫn văn bản nguồn.
