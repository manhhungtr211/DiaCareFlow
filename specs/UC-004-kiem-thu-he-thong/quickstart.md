# Quickstart: Kiểm thử hệ thống (UC-004)

Tài liệu này hướng dẫn cách chạy bộ test tự động để đánh giá hệ thống DiaCareFlow.

## Prerequisites
- Qdrant đang chạy.
- Đã nạp thành công tài liệu (chạy `python -m src.cli ingest ...`).
- Đã có file test data tại `data/test_cases.json`.

## Run Evaluation

Khởi chạy script test qua CLI:

```bash
python -m src.cli evaluate --data data/test_cases.json
```

## Expected Outcome

Hệ thống sẽ chạy qua toàn bộ 20 test cases, báo cáo tiến độ và sau đó hiển thị bảng tổng kết:

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 System Evaluation Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total Test Cases: 20
  Passed: 20
  Failed: 0
  
  Guardrail Coverage: 100%
  Retrieval Accuracy: 100%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Nếu có câu thất bại, hệ thống sẽ in danh sách câu hỏi kèm theo lý do.
