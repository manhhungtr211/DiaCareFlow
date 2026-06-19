# Research: UC-001 — Hỏi đáp Y khoa về Tiểu đường

**Date**: 2026-06-19 | **Spec**: [UC-001-hoi-dap-tieu-duong.md](../use-cases/UC-001-hoi-dap-tieu-duong.md)

## 1. Retrieval Strategy

**Decision**: Sử dụng Qdrant client để truy vấn top-k chunks (k=3) bằng cosine similarity.

**Rationale**: Qdrant đã chạy sẵn từ UC-003, collection `medical_documents` đã có dữ liệu. Dùng cùng embedding model (`keepitreal/vietnamese-sbert`) để tạo query vector, đảm bảo tương thích với vectors đã lưu.

## 2. LLM cho sinh câu trả lời

**Decision**: Google Gemini API (`gemini-2.0-flash`) qua `langchain-google-genai`.

**Rationale**: Đã có `GOOGLE_API_KEY` trong `.env`. Gemini 2.0 Flash miễn phí tier cao, hỗ trợ tiếng Việt tốt, latency thấp (đáp ứng SC-001: <10 giây).

**Alternatives**: Ollama local (offline nhưng chậm hơn, cần GPU)

## 3. Prompt Template

**Decision**: System prompt cố định bằng tiếng Việt, yêu cầu LLM:
- Chỉ trả lời dựa trên context được cung cấp
- Nếu không tìm thấy thông tin → nói rõ "không tìm thấy trong tài liệu"
- Ngôn ngữ phổ thông, dễ hiểu

**Rationale**: Đáp ứng FR-003, FR-005.

## 4. Guardrail (lọc câu hỏi)

**Decision**: Guardrail đơn giản dựa trên keyword matching + LLM classification.
- Bước 1: Kiểm tra input rỗng / quá dài (>500 từ)
- Bước 2: Dùng LLM phân loại câu hỏi có liên quan đến tiểu đường/y tế hay không
- Nếu không liên quan → từ chối với thông báo thân thiện

**Rationale**: Đáp ứng FR-006 và edge cases trong spec. MVP không cần NLP phức tạp.

## 5. Giao diện tương tác

**Decision**: CLI interactive loop (terminal). Người dùng gõ câu hỏi → nhận câu trả lời → tiếp tục hoặc thoát.

**Rationale**: MVP Tuần 1 chưa cần UI (theo Assumptions trong spec).
