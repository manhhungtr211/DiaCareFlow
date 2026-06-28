# Data Model & Contracts: UC-007 Giao diện Chat

## Entities

### `Message` (Frontend State)
Quản lý lịch sử hội thoại hiển thị trên giao diện.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Unique identifier (e.g., uuid hoặc timestamp) |
| `role` | `string` | `"user"` hoặc `"bot"` hoặc `"error"` |
| `content` | `string` | Nội dung tin nhắn (câu hỏi hoặc câu trả lời) |
| `isRefused` | `boolean` | `true` nếu câu trả lời bị từ chối (để render styling cảnh báo) |

## API Contracts (Frontend → Backend)

### 1. `POST /api/chat`
Endpoint xử lý chat với AI.

**Request Payload (JSON)**:
```json
{
  "question": "string (1-2000 chars)"
}
```

**Response**:
Backend hiện tại trả về một raw `string` chứa nội dung câu trả lời (do `response_model=str`).
Frontend sẽ parse response bằng `.text()` thay vì `.json()`. 

*Note: Nếu chuỗi trả về từ chối (is_refused), frontend sẽ kiểm tra text (vd: "Xin lỗi, tôi không thể kê đơn thuốc.") để quyết định set `isRefused: true` cho message.*

### 2. `GET /api/health`
Dùng để kiểm tra trạng thái backend trước khi chat (có thể dùng ở màn hình init để hiển thị E1).

**Response (JSON)**:
```json
{
  "status": "ok" | "degraded",
  "qdrant": "connected" | "disconnected",
  "version": "1.0.0"
}
```
