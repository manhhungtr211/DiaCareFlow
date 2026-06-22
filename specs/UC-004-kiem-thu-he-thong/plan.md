# Implementation Plan: UC-004 Kiểm thử Hệ thống

**Input**: Feature specification from `/specs/use-cases/UC-004-kiem-thu-he-thong.md`

## Summary

Xây dựng một script kiểm thử tự động để đánh giá pipeline RAG và hệ thống Guardrail của DiaCareFlow. Script này sẽ đọc danh sách 20 câu hỏi test mẫu (bao gồm các loại an toàn, kê đơn, chẩn đoán, cấp cứu), chạy qua hệ thống và đánh giá các metrics: Retrieval Accuracy (%) và Guardrail Coverage (%).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: script Python chuẩn import pipeline.

**Storage**: `data/test_cases.json` để lưu trữ câu hỏi test mẫu.

**Testing**: Chạy script CLI (`python -m src.cli evaluate`) hoặc script độc lập (`python scripts/evaluate.py`).

**Target Platform**: Local / Terminal

**Project Type**: CLI Script / Testing Utility

**Performance Goals**: Toàn bộ 20 câu hỏi phải chạy xong trong vòng 10 phút (vì sử dụng LLM API free nên cần giới hạn tốc độ).

**Constraints**: Hệ thống test phải tiếp tục chạy khi gặp lỗi từng câu, không dừng toàn bộ pipeline.

**Scale/Scope**: 20 test cases mẫu.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Pass. Tính năng này tuân thủ yêu cầu đơn giản và là script kiểm thử (Testing & Evaluation) cho MVP Tuần 1.

## Project Structure

### Documentation (this feature)

```text
specs/UC-004-kiem-thu-he-thong/
├── plan.md              # This file
├── research.md          # Output nghiên cứu
├── data-model.md        # Cấu trúc Test Case
├── quickstart.md        # Hướng dẫn chạy test
└── tasks.md             # Sẽ được sinh bởi /speckit-tasks
```

### Source Code (repository root)

```text
src/
├── evaluation/
│   ├── __init__.py
│   ├── data_models.py       # Pydantic/dataclass cho TestCase, TestResult, TestReport
│   └── runner.py            # Script chạy evaluate (chứa loop, catch error, tính toán)
└── cli.py                   # Bổ sung lệnh 'evaluate'

data/
└── test_cases.json          # File chứa 20 test cases mẫu
```

**Structure Decision**: Tích hợp luồng evaluation vào thư mục `src/evaluation/` và xuất ra ngoài CLI qua `src.cli evaluate` để đồng nhất với lệnh `ask` và `ingest`.
