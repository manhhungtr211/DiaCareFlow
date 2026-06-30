# Implementation Plan: UC-007 Giao diện Chat ReactJS

Bản kế hoạch triển khai cho giao diện chat ReactJS giao tiếp với FastAPI Backend đã được xây dựng trong UC-006.

## Technical Context
- **Frontend Stack**: Vite + React (TypeScript) nằm trong thư mục `frontend/`.
- **Backend API**: `POST http://localhost:8000/api/chat` trả về raw `str`.
- **CSS Styling**: Vanilla CSS với CSS Variables cho branding y tế (Xanh dương, Xanh lá, Trắng). Không dùng thư viện UI hay Tailwind.

## Constitution Check
*(Chưa có nguyên tắc cụ thể trong constitution.md ngoài cấu trúc boilerplate)*
- Giao diện đáp ứng tính độc lập (nằm riêng trong thư mục frontend).
- Đơn giản, gọn nhẹ.
- Phân chia thành các component riêng biệt: pages, service, hooks, asses, jsx riêng, css riêng,....
## Proposed Changes

### Phase 1: Khởi tạo dự án Vite React
- Tạo thư mục `frontend` qua Vite: `npm create vite@latest frontend -- --template react-ts`.
- Dọn dẹp boilerplate mặc định của Vite, cấu trúc lại `index.html` và `package.json`.

### Phase 2: Hệ thống CSS & Branding
 Định nghĩa biến CSS (`--primary-blue`, `--emerald-green`, v.v.), typography và cấu hình reset CSS toàn cục.
Styling cho giao diện chat: bong bóng (chat bubbles), vùng tin nhắn, input form và trạng thái loading. Thêm class riêng cho tin nhắn từ chối.

### Phase 3: Xây dựng Giao diện & Logic

  - State quản lý lịch sử chat: `messages` (`{ id, role, content, isRefused }`).
  - Hàm `sendMessage`: gọi API `/api/chat` bằng `fetch`, xử lý kết quả dạng text, bắt lỗi E1, E2.
  - Tự động cuộn xuống cuối màn hình (`scrollIntoView`).

## Verification Plan

### Manual Verification
1. Chạy backend FastAPI (UC-006).
2. Chạy frontend: `cd frontend && npm run dev`.
3. Kiểm thử luồng thành công: Hỏi câu bình thường và nhận câu trả lời.
4. Kiểm thử luồng từ chối: Hỏi câu vi phạm chính sách và kiểm tra UI cảnh báo.
5. Kiểm thử lỗi mạng: Dừng Backend và xem thông báo lỗi hiển thị trên UI.
