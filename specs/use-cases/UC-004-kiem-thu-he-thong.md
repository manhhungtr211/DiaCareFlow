# Feature Specification: UC-004 — Kiểm thử Chất lượng Hệ thống (Testing & Evaluation)

**Feature ID**: `UC-004`

**Input**: BR-001 (MVP Tuần 1) — Luồng kiểm thử: Chạy bộ test tự động (khoảng 20 câu hỏi mẫu) để đánh giá đồng thời chất lượng RAG (retrieval accuracy) và độ tin cậy Guardrail (100% chặn truy vấn nguy hiểm).

---

## Main Flow *(mandatory)*

1. Người vận hành chuẩn bị bộ test tự động (khoảng 20 câu hỏi mẫu bao gồm an toàn và nguy hiểm).
2. Người vận hành chạy script test toàn diện hệ thống.
3. Script tự động gửi từng câu hỏi vào hệ thống (Guardrail → RAG).
4. Script ghi nhận kết quả cho từng câu hỏi (Câu trả lời hợp lệ / Từ chối hợp lệ / Lỗi).
5. Script tính toán các chỉ số Retrieval Accuracy (%) và Guardrail Coverage (%).
6. Script tạo và hiển thị báo cáo tổng kết trên Terminal, highlight các câu hỏi thất bại.

## Alternative Flows

- 2a. Người vận hành muốn test nhanh 1 câu hỏi cụ thể, họ gửi trực tiếp câu hỏi qua Terminal và hệ thống hiển thị kết quả chi tiết (phân loại Guardrail, context, answer).
- 3a. Nếu hệ thống gặp lỗi kỹ thuật ở một câu hỏi, script ghi nhận lỗi cho câu hỏi đó và tiếp tục chạy các câu hỏi còn lại.

## Acceptance Criteria

1. **Given** hệ thống đã nạp tài liệu và cấu hình Guardrail,
**When** người vận hành chạy script test chứa 20 câu hỏi mẫu,
**Then** script chạy qua tất cả câu hỏi và hiển thị kết quả từng câu.

2. **Given** script đã chạy xong,
**When** người vận hành xem báo cáo,
**Then** báo cáo hiển thị tổng kết: Retrieval Accuracy (%) và Guardrail Coverage (%).

3. **Given** kết quả test,
**When** Retrieval Accuracy < 90% hoặc Guardrail Coverage < 100%,
**Then** báo cáo highlight rõ các câu hỏi thất bại để người vận hành debug.

4. **Given** hệ thống đang chạy,
**When** người vận hành gửi 1 câu hỏi test nhanh qua Terminal,
**Then** hệ thống hiển thị kết quả chi tiết: phân loại Guardrail, context truy xuất (nếu an toàn), và câu trả lời cuối cùng.

### Edge Cases

- Bộ test chứa câu hỏi trùng lặp → Script vẫn chạy bình thường, tính mỗi câu là 1 test case riêng.
- Hệ thống gặp lỗi kỹ thuật giữa chừng (ví dụ: mất kết nối Qdrant) → Script ghi nhận lỗi cho câu hỏi đó và tiếp tục chạy các câu hỏi còn lại.
- Bộ test chứa câu hỏi bằng ngôn ngữ khác → Kết quả được ghi nhận, không crash.
- File test_cases trống → Script báo lỗi "không có test case".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI cung cấp một script test có thể chạy qua Terminal để đánh giá toàn bộ pipeline (Guardrail → RAG).
- **FR-002**: Bộ test PHẢI chứa ít nhất 20 câu hỏi mẫu, bao gồm: câu hỏi an toàn (≥10), câu hỏi kê đơn (≥3), câu hỏi chẩn đoán (≥3), câu hỏi cấp cứu (≥3).
- **FR-003**: Với mỗi câu hỏi an toàn, script PHẢI đánh giá xem context truy xuất có chứa thông tin đúng từ tài liệu nguồn không.
- **FR-004**: Với mỗi câu hỏi nguy hiểm, script PHẢI đánh giá xem Guardrail có chặn thành công không.
- **FR-005**: Script PHẢI tạo báo cáo tổng kết sau khi chạy xong, bao gồm: Retrieval Accuracy (%), Guardrail Coverage (%), danh sách câu hỏi thất bại.
- **FR-006**: Script PHẢI tiếp tục chạy khi gặp lỗi ở một câu hỏi cụ thể (không dừng toàn bộ).

### Key Entities

- **Test Case**: Một câu hỏi mẫu kèm loại (an toàn/kê đơn/chẩn đoán/cấp cứu) và kết quả mong đợi.
- **Kết quả Test (Test Result)**: Kết quả chạy từng test case (Đúng/Sai/Từ chối/Lỗi).
- **Báo cáo Test (Test Report)**: Tổng hợp kết quả toàn bộ bộ test, bao gồm metrics tổng quan.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Retrieval Accuracy đạt ≥ 90% trên bộ test câu hỏi an toàn (ít nhất 9/10 câu trả về context đúng).
- **SC-002**: Guardrail Coverage đạt 100% trên bộ test câu hỏi nguy hiểm (tất cả câu kê đơn/chẩn đoán/cấp cứu đều bị chặn).
- **SC-003**: Báo cáo test được tạo tự động và hiển thị rõ ràng trên Terminal sau khi chạy xong.
- **SC-004**: Toàn bộ bộ test (20 câu) chạy xong trong vòng 5 phút.

## Assumptions

- Bộ test câu hỏi mẫu sẽ được soạn thủ công, không tự động sinh.
- Đánh giá Retrieval Accuracy ở MVP là thủ công (kiểm tra mắt) hoặc bán tự động (so sánh keyword) — chưa cần metric phức tạp (RAGAS, faithfulness, etc.).
- Script test chạy qua Terminal (Python), không cần giao diện.
- Kết quả test được hiển thị trên Terminal và có thể lưu ra file (text/JSON) để tham khảo sau.
