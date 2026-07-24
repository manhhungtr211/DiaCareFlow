# Implementation Plan: UC-014: Khởi tạo mô hình BGE-M3

**Branch**: `UC-014-save-embedding-para` | **Date**: 2026-07-24 | **Spec**: [UC-014-save embedding para.md](file:///h:/project/DiaCareFlow/specs/use-cases/UC-014-save%20embedding%20para.md)

**Input**: Feature specification from `/specs/use-cases/UC-014-save embedding para.md`

## Summary

Tích hợp việc tải và lưu trữ trong bộ nhớ (in-memory) mô hình embedding BGE-M3 (`BAAI/bge-m3`) thông qua **FastAPI Lifespan** ngay khi ứng dụng khởi động. Điều này giúp giảm độ trễ khi xử lý các request đầu tiên và tối ưu hóa việc quản lý resource của mô hình. 

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, FlagEmbedding (BGEM3FlagModel)
**Project Type**: Web API (Backend)
**Performance Goals**: Mô hình embedding phải được tải vào bộ nhớ trước khi sẵn sàng nhận requests. Tránh việc reload mô hình cho mỗi request.
**Constraints**: 
- Phải dùng cơ chế `lifespan` mới của FastAPI.
- Thực hiện cơ chế retry tối đa 3 lần nếu việc load mô hình thất bại.
- Nếu load thất bại 3 lần, ứng dụng sẽ log lỗi và yêu cầu tải file BGE-M3 về thư mục `src/agents/embedding_model/bge-m3`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ Không có conflict.

## Project Structure

### Documentation (this feature)

```text
specs/use-cases/
├── UC-014-plan.md              # This file
├── UC-014-research.md          # Research about FastAPI lifespan
└── UC-014-quickstart.md        # Quickstart/validation guide
```

### Source Code

```text
src/
├── api/
│   └── main.py                 # (MODIFY) Cập nhật lifespan để load BGE-M3
└── tools/rag/qa/
    └── retriever.py            # (MODIFY) Sử dụng model được truyền từ memory thay vì khởi tạo mới
```

**Structure Decision**: Cập nhật `src/api/main.py` để dùng `@asynccontextmanager def lifespan(app: FastAPI):`. Mô hình BGE-M3 sẽ được load và gán vào `app.state.embedding_model`. Các route handler hoặc retriever sẽ lấy mô hình từ biến này.

## Proposed Changes / Design

### 1. Quản lý trạng thái mô hình
Trong `src/api/main.py`, định nghĩa `lifespan` context manager:
- Khởi tạo vòng lặp retry (tối đa 3 lần).
- Load mô hình từ thư mục local: `src/agents/embedding_model/bge-m3`.
- Khi load thành công, gán biến `app.state.embedding_model = model`.
- Nếu thất bại sau 3 lần, log ra thông báo lỗi và thoát (`sys.exit(1)` hoặc raise Exception).

### 2. Tái sử dụng mô hình trong Retriever
Trong `src/tools/rag/qa/retriever.py`, sửa đổi hàm `retrieve()` để nhận vào đối tượng `embedding_model` thay vì tự khởi tạo lại bằng `BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)` mỗi lần gọi.
Tại `src/api/main.py` (hoặc `routers`), khi gọi pipeline LangGraph, cần đảm bảo truyền `app.state.embedding_model` vào AgentState hoặc Node Config để `retriever` có thể tái sử dụng hoặc khi nào cần.

## User Review Required

- **Cách truyền Model**: Bạn có muốn sử dụng Dependency Injection của FastAPI để truyền model từ `app.state` xuống router, sau đó truyền vào LangGraph State, rồi cuối cùng truyền vào `retriever` hoặc các biến cần sử dụng không? (Đây là cách an toàn và clean nhất).
- **Đường dẫn thư mục**: Hiện tại thư mục `src/agents/embedding_model/bge-m3` đã có chứa file mô hình thực tế chưa? Nếu chưa có, ứng dụng sẽ báo lỗi ngay khi khởi động. -> sử dụng lệnh tải ngay khi khởi tạo model
