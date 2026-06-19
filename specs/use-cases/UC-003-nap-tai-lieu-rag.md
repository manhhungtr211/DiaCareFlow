# Feature Specification: UC-003 — Nạp Tài liệu Y khoa vào Hệ thống RAG

**Feature ID**: `UC-003`


**Input**: BR-001 (MVP Tuần 1) — Luồng chuẩn bị dữ liệu: Nạp tài liệu PDF tiền tiểu đường vào hệ thống RAG (đọc, chunking, embedding, lưu vào Qdrant) để phục vụ truy xuất kiến thức.

---

## Preconditions
- Đã có tài liệu ở raw_data
- Qrant đã được khởi động

## Main Flow *(mandatory)*

1. Người vận hành chuẩn bị một hoặc nhiều file PDF y khoa về tiền tiểu đường.
2. Người vận hành chạy script nạp tài liệu vào hệ thống RAG.
3. Script tự động đọc nội dung text từ file PDF.
4. Hệ thống chia nhỏ nội dung thành các đoạn (chunks) phù hợp.
5. Hệ thống tạo embedding vector cho từng chunk.
6. Hệ thống lưu trữ các chunk và embedding vào kho kiến thức Qdrant.
7. Hệ thống báo cáo kết quả nạp dữ liệu (số chunks thành công, số lỗi).

## Alternative Flows

- 3a. Nếu file PDF bị lỗi, không đọc được hoặc không có text, hệ thống báo lỗi rõ ràng và dừng nạp file đó.

## Acceptance Criteria

1. **Given** một file PDF tiền tiểu đường hợp lệ,
**When** người vận hành chạy script nạp tài liệu,
**Then** hệ thống đọc được toàn bộ nội dung text từ PDF, chia thành các chunks, tạo embedding, và lưu vào Qdrant thành công.

2. **Given** script đã chạy xong,
**When** người vận hành kiểm tra kho kiến thức,
**Then** có thể xác nhận số lượng chunks đã nạp và xem trước nội dung mẫu của vài chunks.

3. **Given** file PDF bị lỗi hoặc không đọc được,
**When** người vận hành chạy script,
**Then** hệ thống báo lỗi rõ ràng (tên file, lý do lỗi) và không nạp dữ liệu hỏng vào Qdrant.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI đọc được nội dung text từ file PDF tiếng Anh.
- **FR-002**: Hệ thống PHẢI chia nội dung thành các đoạn nhỏ (chunks) với kích thước phù hợp cho retrieval.
- **FR-003**: Hệ thống PHẢI tạo embedding vector cho từng chunk.
- **FR-004**: Hệ thống PHẢI lưu trữ các chunk và embedding vào kho kiến thức (vector database) là Qdrant.
- **FR-005**: Hệ thống PHẢI báo cáo kết quả nạp dữ liệu (số chunks thành công, số lỗi, thời gian xử lý).
- **FR-006**: Hệ thống PHẢI báo lỗi rõ ràng khi file PDF không đọc được.

### Key Entities

- **Tài liệu nguồn (Source PDF)**: File PDF y khoa về tiền tiểu đường, bằng tiếng Anh.
- **Đoạn tài liệu (Chunk)**: Phần nhỏ của tài liệu sau khi chia nhỏ, đơn vị cơ bản cho retrieval.
- **Embedding Vector**: Biểu diễn vector của chunk, dùng cho tìm kiếm ngữ nghĩa.
- **Kho kiến thức**: Nơi lưu trữ chunks + embeddings (Qdrant).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tài liệu PDF tiền tiểu đường được nạp thành công vào kho kiến thức mà không mất dữ liệu text quan trọng.
- **SC-002**: Toàn bộ quá trình nạp (đọc → chunk → embed → lưu) hoàn tất trong thời gian hợp lý (dưới 5 phút cho 1 file PDF ~50 trang).

## Assumptions

- Ở giai đoạn MVP Tuần 1, nạp tài liệu là hành động một lần (batch), chạy qua script/CLI, không phải luồng real-time.
- Chỉ hỗ trợ file PDF có text.
- Tài liệu đầu vào chủ yếu bằng tiếng Việt.
- Kho kiến thức (Qdrant) đã được cài đặt và chạy sẵn ở local trước khi nạp dữ liệu.
- Chiến lược chunking sẽ sử dụng phương pháp đơn giản (fixed-size hoặc paragraph-based), không cần chunking nâng cao ở MVP.
