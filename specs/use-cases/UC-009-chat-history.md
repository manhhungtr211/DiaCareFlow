# UC-009: Quản lý Chat History (Context)

**Feature ID**: `UC-009`
**Input**: BR-003

---

## Actor
- **Người dùng**: Hỏi các câu hỏi liên tiếp trong một phiên chat.

## Trigger
Người dùng đặt một câu hỏi tham chiếu đến (hoặc tiếp nối) nội dung của câu hỏi/câu trả lời trước đó.

## Preconditions
1. Hệ thống đã triển khai RAG và Response Agent cơ bản.

## Main Flow
1. Hệ thống lưu trữ tin nhắn của người dùng và phản hồi của bot vào bộ nhớ tạm (Session History).
2. Người dùng gửi một câu hỏi mới, sử dụng đại từ thay thế (ví dụ: "Bệnh ĐÓ có mấy loại?").
3. Backend truyền lịch sử phiên chat (gần nhất, giới hạn token bằng trim messages) vào context của LLM.
4. LLM dựa vào lịch sử để hiểu "ĐÓ" là gì và trả lời chính xác (không đưa toàn bộ lịch sử vào prompt).

## Acceptance Criteria
1. **Given** người dùng đang trong một phiên chat (đã hỏi "Tiểu đường là gì?"),
   **When** người dùng hỏi một câu hỏi tham chiếu "Vậy bệnh đó có mấy loại?",
   **Then** bot sử dụng chat history để hiểu đúng bối cảnh và trả lời chính xác.
