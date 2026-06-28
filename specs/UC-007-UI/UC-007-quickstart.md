# Quickstart: Validation Guide for UC-007

## Mục đích
Hướng dẫn cách thiết lập, chạy và xác minh Giao diện Chat ReactJS (UC-007) giao tiếp thành công với FastAPI Backend.

## Prerequisites
- Đã cài đặt Node.js (phiên bản >= 18).
- Backend FastAPI (UC-006) đang chạy tại `http://localhost:8000`.

## 1. Thiết lập & Chạy Ứng Dụng

1. Mở terminal mới, di chuyển vào thư mục `frontend`:
   ```bash
   cd frontend
   ```
2. Cài đặt các gói phụ thuộc:
   ```bash
   npm install
   ```
3. Khởi chạy development server:
   ```bash
   npm run dev
   ```
4. Mở trình duyệt và truy cập vào URL được Vite cấp (thường là `http://localhost:5173`).

## 2. Các Kịch Bản Xác Minh (Validation Scenarios)

### Kịch bản 1: Hỏi đáp bình thường (Happy Path)
1. Gõ câu hỏi: `"Tiền tiểu đường là gì?"` vào ô chat.
2. Nhấn phím **Enter** hoặc nút **Gửi**.
3. **Kỳ vọng**: 
   - Ô input sẽ bị xóa trống và disable tạm thời.
   - Hiển thị spinner/loading.
   - Sau vài giây, câu trả lời từ backend sẽ xuất hiện trên màn hình bên dưới câu hỏi.

### Kịch bản 2: Hỏi câu vi phạm chính sách (Refusal Path)
1. Gõ câu hỏi: `"Kê đơn Metformin cho tôi"` vào ô chat.
2. Nhấn **Enter**.
3. **Kỳ vọng**:
   - Backend sẽ trả về đoạn text chứa lời từ chối (vd: "Xin lỗi, tôi không thể kê đơn thuốc").
   - Giao diện có thể đánh dấu nổi bật (viền đỏ) nếu frontend bắt được pattern từ chối này.

### Kịch bản 3: Không kết nối được Backend (Exception E1)
1. Dừng server FastAPI (Ctrl+C trên terminal chạy uvicorn).
2. Gõ bất kỳ câu nào vào ô chat và nhấn **Enter**.
3. **Kỳ vọng**:
   - Giao diện hiển thị thông báo lỗi: `"Không thể kết nối đến server. Vui lòng thử lại sau."`

### Kịch bản 4: Input trống
1. Để trống ô chat và nhấn **Enter**.
2. **Kỳ vọng**:
   - Không có request nào được gửi.
   - (Tùy chọn) Một thông báo nhắc nhở nhỏ hiển thị, hoặc ô input rung lắc báo hiệu.
