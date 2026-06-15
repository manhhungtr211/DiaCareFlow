# Feature Specification: UC-001 — Hỏi đáp Y khoa về Tiểu đường

**Feature ID**: `UC-001`

**Input**: BR-001 (MVP Tuần 1) — Luồng chính: Người dùng đặt câu hỏi an toàn về tiểu đường và nhận câu trả lời dựa trên tài liệu y khoa đã nạp sẵn.

---

## Main Flow *(mandatory)*

1. Người dùng mở hệ thống DiaCareFlow, gõ câu hỏi (ví dụ: "Tiền tiểu đường là gì?" hoặc "Chế độ ăn nào phù hợp cho người tiền tiểu đường?") 
2. Hệ thống phân tích câu hỏi đầu vào thuộc loại an toàn qua lớp Guardrail.
3. Hệ thống truy xuất top-k tài liệu y khoa liên quan nhất từ Qdrant.
4. LLM tổng hợp thông tin từ tài liệu và trả về câu trả lời.

## Alternative Flows 
- 2a. Nếu câu hỏi không an toàn, hệ thống sẽ từ chối trả lời câu hỏi và thông báo cho người dùng biết.

## Acceptance Criteria 

1. **Given** tài liệu về tiền tiểu đường đã được nạp vào hệ thống (Qdrant)
**When** người dùng hỏi "Tiền tiểu đường là gì?",
**Then** hệ thống trả về câu trả lời chứa thông tin chính xác từ tài liệu nguồn, bao gồm định nghĩa và các dấu hiệu nhận biết.

2. **Given** tài liệu về chế độ ăn uống đã được nạp,
**When** người dùng hỏi "Người tiền tiểu đường nên ăn gì?",
**Then** hệ thống trả về lời khuyên dinh dưỡng dựa trên nội dung tài liệu y khoa, không tự sáng tạo thông tin ngoài tài liệu.

3. **Given** tài liệu đã nạp,
**When** người dùng hỏi một câu hỏi mà tài liệu **không** có thông tin (ví dụ: "Phẫu thuật dạ dày có chữa được tiểu đường không?")
**Then** hệ thống trả lời trung thực rằng không tìm thấy thông tin phù hợp trong tài liệu hiện có, thay vì bịa đặt câu trả lời.

### Edge Cases

- Người dùng hỏi câu hỏi không liên quan đến tiểu đường (ví dụ: "Thời tiết hôm nay thế nào?") → Hệ thống nên trả lời rằng chỉ hỗ trợ câu hỏi về tiểu đường.
- Người dùng gửi câu hỏi rất dài (>500 từ) → Hệ thống yêu cầu rút gọn.
- Người dùng gửi câu hỏi trống hoặc chỉ chứa ký tự đặc biệt → Hệ thống trả về thông báo lỗi thân thiện.
- Tài liệu chưa được nạp (Qdrant trống) → Hệ thống thông báo chưa có dữ liệu thay vì trả lời rỗng.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI tiếp nhận câu hỏi dạng văn bản (text) từ người dùng.
- **FR-002**: Hệ thống PHẢI truy xuất các đoạn tài liệu y khoa liên quan nhất (top-k) từ kho kiến thức đã nạp sẵn để làm ngữ cảnh (context) cho câu trả lời.
- **FR-003**: Hệ thống PHẢI tạo câu trả lời dựa trên nội dung tài liệu truy xuất được, không tự bịa đặt thông tin (giảm thiểu hallucination).
- **FR-004**: Hệ thống PHẢI trả về câu trả lời hoàn chỉnh (context + answer) trong thời gian dưới 30 giây ở môi trường local.
- **FR-005**: Khi không tìm thấy thông tin liên quan trong tài liệu, hệ thống PHẢI thông báo trung thực thay vì tạo câu trả lời không có cơ sở.
- **FR-006**: Hệ thống PHẢI từ chối trả lời các câu hỏi hoàn toàn không liên quan đến tiểu đường với thông báo thân thiện.

### Key Entities

- **Câu hỏi (Query)**: Văn bản đầu vào từ người dùng, bằng tiếng việt, liên quan đến tiểu đường.
- **Ngữ cảnh (Context)**: Các đoạn tài liệu y khoa được truy xuất từ kho kiến thức (top-k chunks).
- **Câu trả lời (Answer)**: Phản hồi văn bản được tạo dựa trên ngữ cảnh, trình bày cho người dùng cuối.
- **Tài liệu nguồn (Source Document)**: Tài liệu PDF y khoa về tiền tiểu đường đã được nạp sẵn vào hệ thống.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Người dùng nhận được câu trả lời cho câu hỏi y khoa về tiểu đường trong vòng 10 giây.
- **SC-002**: Ít nhất 90% câu trả lời (trên bộ test 10-20 câu hỏi mẫu) chứa thông tin chính xác, trùng khớp với nội dung tài liệu nguồn.
- **SC-003**: 100% các trường hợp không có thông tin trong tài liệu, hệ thống thông báo trung thực thay vì bịa đặt.
- **SC-004**: Người dùng có thể hiểu được câu trả lời mà không cần kiến thức y khoa chuyên sâu (ngôn ngữ phổ thông).

## Assumptions

- Tài liệu y khoa về tiền tiểu đường (PDF) đã được nạp sẵn vào hệ thống trước khi người dùng bắt đầu hỏi.
- Người dùng chủ yếu sử dụng tiếng Việt để đặt câu hỏi.
- Ở giai đoạn MVP Tuần 1, giao diện người dùng chưa có — tương tác qua Terminal/Script.
- Hệ thống chạy ở môi trường Local/Docker, không yêu cầu kết nối internet cho phần RAG.
- Câu hỏi an toàn (không vi phạm guardrail) sẽ được xử lý bởi use-case này; câu hỏi nguy hiểm được xử lý bởi UC-002.
