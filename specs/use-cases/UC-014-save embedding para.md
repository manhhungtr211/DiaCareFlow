# UC-014: Khởi tạo mô hình BGE-M3

**Feature ID**: `UC-014`

---

## Actor
- **Ứng dụng**: Ứng dụng sử dụng embedding để phân loại các câu.

## Trigger
Khi khởi động ứng dụng, cần khởi tạo embedding mô hình BGE-M3

## Preconditions
1. Ứng dụng cần có file BGE-M3 tại: `src/agents/embedding_model/bge-m3`

## Main Flow
1. Ứng dụng khởi động
2. Ứng dụng khởi tạo embedding mô hình BGE-M3
3. Ứng dụng sẵn sàng nhận yêu cầu từ người dùng

## Extended Flow
3a. Nếu mô hình không thể khởi tạo, re-try tối đa 3 lần
3b. Nếu đã re-try tối đa 3 lần mà mô hình không thể khởi tạo, ứng dụng sẽ thông báo lỗi và yêu cầu người dùng tải file về

## Acceptance Criteria
1. **Given** Ứng dụng khởi động,
   **When** Ứng dụng khởi tạo embedding mô hình BGE-M3,
   **Then** Ứng dụng sẵn sàng nhận yêu cầu từ người dùng

# Note:
1. Lưu lại thông số
2. sử dụng FastAPI Lifespan