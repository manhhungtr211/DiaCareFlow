# Research: UC-003 — Nạp Tài liệu Y khoa vào Hệ thống RAG

**Date**: 2026-06-15

## 1. PDF Reader — Thư viện đọc PDF tiếng Việt

**Decision**: PyMuPDF (`pymupdf` / `fitz`)

**Rationale**:
- Tốc độ nhanh nhất trong các thư viện Python đọc PDF (C-based)
- Hỗ trợ tốt Unicode / tiếng Việt (dấu, ký tự đặc biệt)
- API đơn giản: `page.get_text()` trả về text sạch
- Không cần OCR (file PDF đã có text layer)
- Xử lý được file lớn (~36MB) mà không tốn quá nhiều bộ nhớ

**Alternatives considered**:
- `pdfplumber`: Chậm hơn PyMuPDF, phù hợp hơn cho trích xuất bảng
- `PyPDF2/pypdf`: Đơn giản nhưng chất lượng text extraction kém hơn, hay bị lỗi encoding tiếng Việt
- `unstructured`: Mạnh nhưng heavy, quá phức tạp cho MVP

## 2. Chunking Strategy — Phương pháp chia nhỏ tài liệu

**Decision**: `RecursiveCharacterTextSplitter` từ `langchain-text-splitters`

**Rationale**:
- Phương pháp đơn giản, phù hợp MVP (spec yêu cầu "fixed-size hoặc paragraph-based")
- Chia theo ký tự với chuỗi separator ưu tiên: `["\n\n", "\n", ". ", " ", ""]`
- Giữ ngữ cảnh tốt hơn fixed-size nhờ ưu tiên tách tại ranh giới paragraph/sentence
- Tham số mặc định phù hợp cho RAG:
  - `chunk_size = 1000` ký tự
  - `chunk_overlap = 200` ký tự (20% overlap để không mất ngữ cảnh)

**Alternatives considered**:
- Fixed-size chunking: Quá đơn giản, dễ cắt giữa câu
- Semantic chunking: Cần embedding cho mỗi câu → chậm và phức tạp, không phù hợp MVP
- Markdown/HTML-aware splitting: Không cần vì PDF text không có cấu trúc markup

## 3. Embedding Model — Mô hình tạo vector

**Decision**: Google Generative AI Embeddings (`models/text-embedding-004`)

**Rationale**:
- Phù hợp với tech stack dự án (đang dùng Google AI / Gemini cho LLM)
- Hỗ trợ tốt tiếng Việt (multilingual model)
- Dimension: 768 (mặc định), phù hợp cho Qdrant
- Free tier: 1,500 requests/phút — đủ cho MVP batch processing
- Tích hợp sẵn qua `langchain-google-genai`

**Alternatives considered**:
- OpenAI `text-embedding-3-small`: Tốt nhưng tốn phí, không khớp với Google AI stack
- `sentence-transformers` local: Cần GPU, không phù hợp local dev trên Windows
- Cohere Embed: Tốt cho multilingual nhưng thêm dependency provider khác

## 4. Vector Database — Lưu trữ và truy xuất

**Decision**: Qdrant (chạy local qua Docker, port 6333)

**Rationale**:
- Đã được chọn sẵn trong spec và tech stack (`CLAUDE.md`)
- Hỗ trợ tốt CRUD cho vector data
- Python client (`qdrant-client`) đơn giản, well-documented
- Chạy local qua Docker: `docker run -p 6333:6333 qdrant/qdrant`
- Hỗ trợ payload (metadata) kèm vector — lưu nội dung chunk gốc

**Collection config**:
- Collection name: `medical_documents`
- Vector size: 768 (khớp với embedding model)
- Distance metric: Cosine
- Payload fields: `content` (text gốc), `source` (tên file), `page` (số trang), `chunk_index` (thứ tự chunk)

## 5. CLI Entry Point — Cách chạy script

**Decision**: `argparse` hoặc chạy trực tiếp `python -m src.cli`

**Rationale**:
- MVP chỉ cần chạy từ Terminal, không cần framework CLI phức tạp
- Nhận tham số đầu vào: đường dẫn file/thư mục PDF
- Output: in kết quả ra Terminal (số chunks, thời gian xử lý, lỗi nếu có)

**Alternatives considered**:
- `click` / `typer`: Over-engineering cho MVP — chỉ cần 1 command đơn giản
- FastAPI endpoint: Sẽ dùng khi tích hợp API, nhưng MVP chạy batch

## 6. Error Handling Strategy

**Decision**: Log lỗi chi tiết + skip file lỗi + tiếp tục pipeline

**Rationale**:
- Spec yêu cầu: "Hệ thống báo lỗi rõ ràng (tên file, lý do lỗi) và không nạp dữ liệu hỏng vào Qdrant"
- Mỗi file xử lý độc lập → lỗi 1 file không ảnh hưởng file khác
- Kết thúc pipeline in báo cáo tổng kết: thành công / lỗi / tổng thời gian
