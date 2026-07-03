# UC-010: Trò chuyện thông thường (Bypass RAG)

**Feature ID**: `UC-010`
**Input**: BR-003

---

## Actor
- **Người dùng**: Tương tác giao tiếp cơ bản (chào hỏi, cảm ơn...).

## Trigger
Người dùng gửi các câu "small talk" không yêu cầu kiến thức y khoa.

## Preconditions
1. Agent có khả năng phân loại intent (đối thoại thông thường vs kiến thức chuyên môn).

## Main Flow
1. Người dùng gửi một tin nhắn 
2. Supervior Node nhận diện đây là câu hỏi giao tiếp cơ bản
3. Response Agent trực tiếp phản hồi lại tự nhiên ngay lập tức.

## Extended Flow
2a. Nếu đó là tin nhắn liên quan đến hỏi liên quan đến bệnh tiểu đường, chuyển đến RAG Node

## Acceptance Criteria
1. **Given** một câu nói giao tiếp thông thường,
   **When** người dùng gửi tin nhắn,
   **Then** Response Agent phản hồi tự nhiên ngay lập tức mà không thực hiện truy xuất RAG.
