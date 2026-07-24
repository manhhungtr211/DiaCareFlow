# DiaCareFlow — Hệ thống Intelligent Multi-Agent hỗ trợ tư vấn bệnh tiểu đường

**DiaCareFlow** là một hệ thống AI đa tác vụ (Multi-Agent) chuyên biệt nhằm tư vấn, giải đáp thắc mắc và cung cấp thông tin y khoa liên quan đến bệnh tiểu đường. Dự án sử dụng cấu trúc điều phối linh hoạt qua LangGraph, kết hợp với sức mạnh của nhiều LLM và cơ sở dữ liệu véc-tơ để tối ưu hóa tính chính xác và an toàn.

---

## 🎯 Mục Tiêu Dự Án (Goals)

- Xây dựng hệ thống Intelligent Multi-Agent cá nhân hóa hỗ trợ thông tin bệnh tiểu đường, được điều phối bởi **LangGraph**.
- Đảm bảo an toàn y khoa tuyệt đối: Tích hợp chốt chặn (Guardrails/Triage) phân loại các yêu cầu nguy hiểm, cấp cứu hoặc kê đơn thuốc.
- Kết hợp song song các LLM hàng đầu (**Google Gemini** và **Groq**) để tối ưu chi phí, tốc độ và khả năng suy luận.
- Tích hợp tìm kiếm nội bộ **RAG (Qdrant)** và tìm kiếm trực tuyến thời gian thực qua Web Search pipeline (**SearXNG, Crawl4ai, Jina Reranker**) để cung cấp kiến thức cập nhật.

---

## 🏗 Kiến Trúc Hệ Thống

DiaCareFlow tuân theo thiết kế **Multi-Agent (LangGraph)**, trong đó mỗi nút (node) chịu trách nhiệm một chức năng riêng biệt:

### 1. Kiến trúc Đa Mô Hình (Multi-LLM)
Hệ thống sử dụng hai lớp model độc lập:
- **`ROUTING_MODEL` (via Groq)**: Được dùng bởi `Supervisor` và `Response` để đưa ra quyết định định tuyến tức thời và tổng hợp câu trả lời cuối cùng nhanh chóng (vd: `llama-3.1-70b-versatile` hoặc `gpt-oss-20b`).
- **`TOOL_MODEL` (via Gemini 2.0 Flash)**: Được dùng cho các tác nhân chuyên sâu (Triage, Factor, Suggestion, Harm) yêu cầu phân tích ngữ cảnh dài, trích xuất dữ liệu, và tách các truy vấn con (sub-queries).

### 2. Các Agents Chính
- **Supervisor Agent**: Phân tích lịch sử trò chuyện và câu hỏi mới nhất, sau đó định tuyến luồng xử lý tới các sub-agents tương ứng, hoặc trả lời trực tiếp các câu giao tiếp xã giao (Small talk).
- **Triage Agent (Guardrail)**: Đánh giá câu hỏi đầu vào để chặn các câu hỏi nằm ngoài phạm vi, yêu cầu cấp cứu, hoặc kê đơn.
- **Factor Agent**: Truy xuất nguyên nhân, yếu tố nguy cơ.
- **Suggestion Agent**: Cung cấp các đề xuất, chế độ dinh dưỡng, lối sống.
- **Harm Agent**: Phân tích biến chứng và tác hại của bệnh.
- **Response Agent**: Tổng hợp toàn bộ dữ liệu từ các agents, định dạng markdown chuẩn, và trình bày rõ ràng kèm nguồn trích dẫn.

### 3. Retrieval-Augmented Generation (RAG) & Web Search
- **Embedding**: Sử dụng mô hình `BAAI/bge-m3` (chạy hoàn toàn cục bộ).
- **Vector DB**: Qdrant để lưu trữ và tìm kiếm vector.
- **Web Search Tool**: Cào dữ liệu theo thời gian thực (SearXNG + Crawl4AI) và sử dụng Jina AI để chấm điểm độ liên quan (reranking).

---

## 🚀 Cài Đặt (Setup & Installation)

### Yêu Cầu Hệ Thống
- Python 3.10+
- Docker (Dành cho SearXNG và Qdrant nếu chạy local)

### 1. Cài Đặt Thư Viện

```bash
# Cài đặt requirements
pip install -r requirements.txt

playwright install chromium
```

### 2. Cấu Hình Environment Variables

Tạo tệp `.env` ở thư mục gốc của dự án và khai báo:

```env
# --- API Keys ---
GROQ_API_KEY="your_groq_api_key_here"
GEMINI_API_KEY="your_gemini_api_key_here"
JINA_API_KEY="your_jina_api_key_here"

# --- Models ---
ROUTING_MODEL="llama-3.1-70b-versatile"
TOOL_MODEL="gemini-2.0-flash"

# --- Qdrant DB ---
QDRANT_URL="http://localhost:6333"
QDRANT_COLLECTION="diacareflow_docs"
VECTOR_SIZE=1024

# --- Document Chunking ---
CHUNK_SIZE=2000
CHUNK_OVERLAP=300

# --- Search Tools ---
XNG_SEARCH_URL="http://localhost:8080"
XNG_MAX_RESULTS=5
SCRAPE_TIMEOUT=10
```

### 3. Khởi Chạy Các Services Cơ Bản (Docker)

```bash
# Chạy Qdrant cho Vector DB
docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# Chạy SearXNG cho Web Search
docker run -d --name searxng -p 8080:8080 -v ${PWD}/docker/searxng:/etc/searxng searxng/searxng:latest
```

### 4. Chạy Backend API (FastAPI)

```bash
uvicorn src.api.main:app --reload
```
Server sẽ chạy ở `http://127.0.0.1:8000`. Cung cấp endpoints để giao tiếp với Client và Streaming JSON.

### 5. Chạy Front-end
```bash
cd frontend
npm run dev
```

---

