# Tasks: UC-004 Kiểm thử Hệ thống

**Input**: Design documents from `/specs/UC-004-kiem-thu-he-thong/`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US1]**: Belongs to the single user story: Kiểm thử tự động
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Khởi tạo cấu trúc và chuẩn bị data cho module evaluation

- [x] T001 Tạo thư mục `src/evaluation/` và thêm `src/evaluation/__init__.py`
- [x] T002 [P] Tạo file dữ liệu mẫu `data/test_cases.json` chứa 20 test cases dựa trên cấu trúc trong `data-model.md`

---

## Phase 2: Foundational 

**Purpose**: Định nghĩa các data models dùng chung cho luồng evaluation

- [x] T003 Implement các dataclass/Pydantic models tại `src/evaluation/data_models.py`: `TestCase`, `TestResult`, `TestReport` (theo `data-model.md`)

**Checkpoint**: Models và Test Data sẵn sàng.

---

## Phase 3: User Story 1 - Kiểm thử hệ thống RAG & Guardrail (Priority: P1) 🎯 MVP

**Goal**: Cung cấp lệnh CLI để chạy test toàn diện 20 câu hỏi, báo cáo Guardrail Coverage và Retrieval Accuracy

**Independent Test**: Chạy `python -m src.cli evaluate --data data/test_cases.json` và kiểm tra báo cáo Terminal.

### Implementation for User Story 1

- [x] T004 [US1] Implement evaluation runner tại `src/evaluation/runner.py` (hàm `load_test_cases`, `evaluate_single`, `run_evaluation_suite`)
- [x] T005 [US1] Implement tính năng in báo cáo tại `src/evaluation/runner.py` (hàm `print_report`)
- [x] T006 [US1] Cập nhật `src/cli.py` thêm command `evaluate` nhận tham số `--data` gọi vào `run_evaluation_suite`

**Checkpoint**: Lệnh `evaluate` chạy thành công, report in ra chuẩn format.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Cải thiện chất lượng và test

- [x] T007 Kiểm tra thủ công: Chạy quickstart validation theo `specs/UC-004-kiem-thu-he-thong/quickstart.md` để đảm bảo lệnh hoạt động mượt mà.

---

## Dependencies & Execution Order

- **Phase 1** (Setup): Chạy đầu tiên.
- **Phase 2** (Foundational): T003 phụ thuộc T001.
- **Phase 3** (US1): T004 phụ thuộc T002 và T003. T006 phụ thuộc T004, T005.

## Notes

- [P] tasks = different files, no dependencies
- [US1] = all tasks belong to the single user story
- Commit after each task or logical group
