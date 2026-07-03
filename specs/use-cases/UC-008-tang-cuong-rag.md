# UC-008: Tăng cường độ chính xác RAG

**Feature ID**: `UC-008`
**Input**: BR-003

---

## Actor
- **Người dùng**: Đặt câu hỏi chuyên sâu về bệnh tiểu đường.

## Trigger
Người dùng gửi một câu hỏi chuyên sâu cần truy xuất tài liệu thực tế.

## Preconditions
1. Đã có 1-2 tài liệu tiếng Việt chất lượng cao về tiểu đường được nạp vào vector store.

## Main Flow
1. Người dùng hỏi một câu chuyên sâu về tiểu đường.
2. Hệ thống (RAG Agent) truy xuất dữ liệu từ các tài liệu tiếng Việt mới được nạp.
3. Response Agent tổng hợp và đưa ra câu trả lời chính xác.

## Acceptance Criteria
1. **Given** 1-2 tài liệu tiếng Việt về tiểu đường đã được nạp vào vector store,
   **When** người dùng hỏi về kiến thức trong tài liệu,
   **Then** bot trả lời chính xác dựa trên tài liệu (đạt >90% độ chính xác khi đánh giá thủ công).
