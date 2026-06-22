# Phase 0: Research & Decisions

## Đánh giá Retrieval Accuracy bán tự động

**Vấn đề**: Làm sao để đánh giá xem câu trả lời hoặc context cho câu hỏi an toàn là đúng (accurate) khi chưa có metric phức tạp (như RAGAS hay faithfulness) ở MVP Tuần 1?

**Quyết định**: Sử dụng Keyword-based Matching.
- Mỗi test case an toàn sẽ có một mảng `keywords` chứa các từ khoá bắt buộc hoặc ý chính.
- Trong quá trình chạy test, script sẽ kiểm tra `answer.text` (hoặc context snippets) có chứa ít nhất 1 (hoặc tất cả) các keywords hay không.

**Lý do**: Phù hợp cho MVP vì dễ thực hiện, chạy nhanh và không phụ thuộc vào LLM khác (LLM-as-a-judge).

**Alternative Considered**:
- Kiểm tra bằng tay (Manual Evaluation): Quá chậm nếu test suite phình to.
- Dùng GPT-4 để evaluate: Vượt quá phạm vi MVP và tốn kém chi phí.

## Định dạng file Test Cases

**Quyết định**: Sử dụng định dạng JSON cho `data/test_cases.json`.
- Định dạng JSON dễ dàng parse bằng Python (`json` module).
- Dễ dàng define cấu trúc nested cho array của keywords hoặc object các trường `expected_refusal`.

## Tích hợp Test Runner

**Quyết định**: Viết logic vào `src/evaluation/runner.py` và tạo entry command `evaluate` trong `cli.py`.
- Lệnh chạy sẽ là `python -m src.cli evaluate --data data/test_cases.json`.

**Lý do**: Đồng nhất trải nghiệm dòng lệnh với `ingest` và `ask`. Có thể dễ dàng tích hợp vào CI/CD sau này.


    

