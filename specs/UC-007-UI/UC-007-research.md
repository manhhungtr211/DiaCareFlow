# Research: UC-007 Giao diện Chat ReactJS

## 1. Lựa chọn Frontend Framework
- **Decision**: Sử dụng **Vite + React (TypeScript)** để tạo một Single Page Application (SPA) nằm trong thư mục `frontend/`.
- **Rationale**: Vite cực kỳ nhẹ, build nhanh và lý tưởng cho một giao diện chat tối giản (minimalist) như yêu cầu của UC-007. Sử dụng thư mục `frontend/` giúp tách biệt hoàn toàn mã nguồn UI khỏi backend FastAPI (nằm ở `src/` và thư mục gốc).
- **Alternatives considered**: 
  - *Next.js*: Quá nặng và phức tạp (cần server SSR) cho một giao diện tĩnh đơn giản gọi API ngoài.
  - *Create React App (CRA)*: Đã lỗi thời và chậm, cộng đồng chuyển sang Vite.

## 2. Quản lý State & Gọi API
- **Decision**: Sử dụng `fetch` API gốc của trình duyệt và `useState`, `useRef` (để scroll xuống cuối) của React.
- **Rationale**: Endpoint đơn giản (chỉ có `/api/chat` và `/api/health`). Ứng dụng chỉ cần gửi text và nhận text, việc sử dụng thư viện như axios hay React Query là over-engineering cho MVP này.
- **Alternatives considered**: *Axios / React Query* (không cần thiết vì data fetching rất cơ bản).

## 3. Styling & CSS
- **Decision**: Sử dụng Vanilla CSS với CSS Variables cho branding y tế (Xanh dương, Xanh lá, Trắng).
- **Rationale**: Tuân thủ hướng dẫn kỹ thuật không sử dụng TailwindCSS trừ khi user yêu cầu. Vanilla CSS dễ dàng tạo được giao diện tinh tế, viền mềm mại, và gradient y tế (medical branding).
- **Alternatives considered**: *Tailwind CSS* (không dùng do quy định của system).

## 4. Xử lý CORS và Kết nối Backend
- **Decision**: Backend (đã cấu hình cho phép `*`) chạy ở `http://localhost:8000`. Frontend sẽ gọi trực tiếp đến URL này.
- **Rationale**: CORS đã được xử lý ở backend (UC-006).

## NEEDS CLARIFICATION (Đã giải quyết)
- **Vị trí code**: Frontend sẽ được đặt tại `./frontend/`.
- **Cấu trúc JSON Backend**: Backend trả về raw string `text`, nhưng request vẫn gửi dạng json `{"question": "..."}`. Wait, theo sửa đổi mới nhất của User trên Backend, `response_model=str` và trả về một raw string. Nhưng `fetch()` sẽ nhận được text. Do đó, parse response backend bằng `response.text()` thay vì `response.json()`.
