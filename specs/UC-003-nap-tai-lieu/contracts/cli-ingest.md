# CLI Contract: UC-003 — Nạp Tài liệu Y khoa

**Date**: 2026-06-15

## Command Interface

### `ingest` — Nạp tài liệu PDF vào Qdrant

```bash
python -m src.cli ingest <path> [options]
```

### Arguments

| Argument | Type   | Required | Description                                    |
|----------|--------|----------|------------------------------------------------|
| `path`   | string | ✅       | Đường dẫn tới file PDF hoặc thư mục chứa PDFs |

### Options

| Option              | Type   | Default             | Description                          |
|---------------------|--------|---------------------|--------------------------------------|
| `--collection`      | string | `medical_documents` | Tên Qdrant collection                |
| `--chunk-size`      | int    | `1000`              | Kích thước chunk (ký tự)             |
| `--chunk-overlap`   | int    | `200`               | Overlap giữa chunks (ký tự)         |
| `--qdrant-url`      | string | `http://localhost:6333` | URL của Qdrant server           |

### Output Format (stdout)

**Khi thành công:**
```
📄 Processing: BMC_Diabetes_Handout_2024_vie.pdf
   Pages: 120 | Chunks: 245 | ✅ Uploaded to Qdrant

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Ingestion Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Files processed: 1
  Successful: 1
  Failed: 0
  Total chunks: 245
  Time elapsed: 42.3s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Khi có lỗi:**
```
📄 Processing: corrupt_file.pdf
   ❌ Error: PDFReadError — Cannot extract text from file (possibly scanned/image-only PDF)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Ingestion Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Files processed: 2
  Successful: 1
  Failed: 1
  Total chunks: 245
  Time elapsed: 45.1s

  ⚠️ Failed files:
    - corrupt_file.pdf: PDFReadError — Cannot extract text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Exit Codes

| Code | Meaning                                |
|------|----------------------------------------|
| `0`  | Tất cả files nạp thành công            |
| `1`  | Một hoặc nhiều files bị lỗi           |
| `2`  | Lỗi hệ thống (Qdrant unreachable, etc.) |

### Error Output (stderr)

Lỗi hệ thống và stack traces được ghi ra stderr, tách biệt với output chính trên stdout.
