# Spec: UC-010 Bypass RAG

**Feature ID**: `UC-010`
**Source**: `specs/use-cases/UC-010-bypass-rag.md`

---

## Actor
- **Người dùng**: Tương tác giao tiếp cơ bản (chào hỏi, cảm ơn...).

## Trigger
Người dùng gửi các câu "small talk" không yêu cầu kiến thức y khoa.

## Preconditions
1. Agent có khả năng phân loại intent (đối thoại thông thường vs kiến thức chuyên môn).

## User Stories

### US1 (P1) — Intent Classification in Supervisor
**As a** user sending a casual greeting or thanks,
**I want** the chatbot to respond immediately without searching the database,
**So that** I get a fast, natural reply.

### US2 (P1) — RAG Routing for Diabetes Questions
**As a** user asking about diabetes or health topics,
**I want** the chatbot to still retrieve relevant documents before answering,
**So that** I get accurate, document-grounded responses.

## Acceptance Criteria
1. **Given** a casual greeting (e.g., "Chào bác sĩ", "Cảm ơn bạn"),
   **When** the user sends the message,
   **Then** the Response Agent replies naturally without performing RAG retrieval (`rag_agent` not in `nodes_visited`).

2. **Given** a diabetes-related question (e.g., "Bệnh tiểu đường nên ăn gì?"),
   **When** the user sends the message,
   **Then** the pipeline routes through `rag_agent` before `response_agent`.
