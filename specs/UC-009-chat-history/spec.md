# Spec: UC-009 Quản lý Chat History (Context)

**Feature ID**: `UC-009`
**Source**: `specs/use-cases/UC-009-chat-history.md`

---

## Actor
- **Người dùng**: Hỏi các câu hỏi liên tiếp trong một phiên chat.

## Trigger
Người dùng đặt một câu hỏi tham chiếu đến (hoặc tiếp nối) nội dung của câu hỏi/câu trả lời trước đó.

## Preconditions
1. Hệ thống đã triển khai RAG và Response Agent cơ bản (UC-001, UC-005).
2. Supervisor Agent đã phân loại intent (UC-010).

## User Stories

### US1 (P1) — Session History Storage
**As a** user chatting with DiaCareFlow,
**I want** the system to remember my previous messages in the current session,
**So that** I don't have to repeat context for follow-up questions.

### US2 (P1) — Contextual Coreference Resolution
**As a** user asking a follow-up question using pronouns (e.g., "bệnh ĐÓ có mấy loại?"),
**I want** the LLM to understand what "ĐÓ" refers to based on chat history,
**So that** I get an accurate, contextually aware response.

### US3 (P2) — Token-Limited History Window
**As a** system operator,
**I want** the chat history sent to the LLM to be trimmed to a configurable token limit,
**So that** we don't exceed LLM context windows or incur unnecessary API costs.

## Acceptance Criteria
1. **Given** người dùng đang trong một phiên chat (đã hỏi "Tiểu đường là gì?"),
   **When** người dùng hỏi một câu hỏi tham chiếu "Vậy bệnh đó có mấy loại?",
   **Then** bot sử dụng chat history để hiểu đúng bối cảnh và trả lời chính xác.

2. **Given** a session with 20+ message exchanges,
   **When** the user sends a new message,
   **Then** the system trims the history to stay within the configured token limit using `trim_messages`.

3. **Given** a new browser session (page refresh or new tab),
   **When** the user sends the first message,
   **Then** the chat history starts empty (no persistence across sessions).
