# Data Model: UC-001 — Hỏi đáp Y khoa về Tiểu đường

**Date**: 2026-06-19

## Entities

### Query (Câu hỏi đầu vào)

| Field        | Type   | Constraint                     |
|-------------|--------|-------------------------------|
| `text`      | `str`  | Không rỗng, ≤500 từ          |
| `timestamp` | `datetime` | Tự động gán                |

### RetrievedContext (Ngữ cảnh truy xuất)

| Field        | Type              | Description                       |
|-------------|-------------------|-----------------------------------|
| `chunks`    | `list[ChunkResult]` | Top-k chunks từ Qdrant         |
| `query_vector` | `list[float]`  | Vector embedding của câu hỏi   |

### ChunkResult

| Field     | Type    | Description                    |
|----------|---------|-------------------------------|
| `content`| `str`   | Nội dung đoạn tài liệu        |
| `source` | `str`   | Tên file nguồn                 |
| `score`  | `float` | Cosine similarity score        |

### Answer (Câu trả lời)

| Field          | Type              | Description                    |
|---------------|-------------------|-------------------------------|
| `text`        | `str`             | Nội dung trả lời              |
| `sources`     | `list[ChunkResult]` | Nguồn tài liệu đã dùng     |
| `is_refused`  | `bool`            | True nếu câu hỏi bị từ chối  |
| `refuse_reason`| `str \| None`    | Lý do từ chối (nếu có)       |

### GuardrailResult (Kết quả kiểm tra an toàn)

| Field       | Type   | Description                      |
|------------|--------|----------------------------------|
| `is_safe`  | `bool` | Câu hỏi có an toàn để xử lý?   |
| `reason`   | `str \| None` | Lý do từ chối (nếu có)   |

## Relationships

```
Query → GuardrailResult → RetrievedContext → Answer
         (filter)          (retrieve)        (generate)
```

## State Flow

```
[Input] → [Validate] → [Guardrail Check]
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
               [Safe]           [Unsafe]
                    │                 │
                    ▼                 ▼
            [Retrieve top-k]    [Refuse Answer]
                    │
                    ▼
           [Generate Answer]
                    │
                    ▼
              [Return Answer]
```
