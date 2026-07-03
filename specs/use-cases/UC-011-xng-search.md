# UC-011: Tích hợp XNG Search (Web Search)

**Feature ID**: `UC-011`
**Input**: BR-003

---

## Actor
- **Người dùng**: Hỏi thông tin thực tế, cập nhật mới nhất không có trong tài liệu nội bộ.

## Trigger
Người dùng hỏi một câu kiến thức nằm ngoài phạm vi tài liệu RAG đã nạp.

## Preconditions
1. Đã tích hợp API của công cụ tìm kiếm XNG Search (hoặc tương tự).
2. Hệ thống Agent có khả năng nhận biết "không biết" từ dữ liệu nội bộ.

## Main Flow
1. Người dùng hỏi một câu hỏi đòi hỏi thông tin ngoài luồng hoặc tin tức mới.
2. RAG Agent không tìm thấy thông tin phù hợp trong vector store.
3. Hệ thống kích hoạt công cụ XNG Search để tìm kiếm trên web.
4. Response Agent tổng hợp kết quả từ web và trả lời người dùng.

## Acceptance Criteria
1. **Given** câu hỏi đòi hỏi thông tin thực tế ngoài tài liệu chuyên môn đã nạp,
   **When** RAG không có dữ liệu,
   **Then** bot sử dụng công cụ XNG Search để tìm kiếm thông tin và tổng hợp câu trả lời.
