# BỘ CÂU HỎI & KỊCH BẢN TRẢ LỜI PHỎNG VẤN DỰ ÁN DIACAREFLOW
> **Tập trung vào:** Tư duy thiết kế (Why X and not Y?), Lý giải con số kết quả (Metrics), và Xử lý sự cố (Troubleshooting).

---

## 📌 PHẦN 1: GIỚI THIỆU DỰ ÁN TRONG 60 GIÂY (PITCH)

**Q: Em hãy giới thiệu tổng quan về dự án DiaCareFlow?**

* **Trả lời:**
  > "DiaCareFlow là hệ thống AI Multi-Agent chuyên sâu hỗ trợ tư vấn và giải đáp thắc mắc về bệnh tiểu đường. 
  > Dự án được em thiết kế theo kiến trúc **Multi-Agent (LangGraph)** kết hợp **Dual-LLM (Groq + Gemini 2.0 Flash)** và **Hybrid Retrieval (Qdrant RAG + Web Search)**. 
  > Hệ thống giải quyết 2 bài toán lớn trong ứng dụng y tế: **đảm bảo an toàn 100% khi phân loại câu hỏi nguy hiểm/kê đơn** và **tối ưu tốc độ phản hồi (sub-2.5s retrieval) cùng chi phí API (giảm ~40%)**."

---

## 📌 PHẦN 2: CÁC CÂU HỎI ĐỊNH HƯỚNG KIẾN TRÚC ("SAO PHẢI LÀM CÁI NÀY MÀ KHÔNG PHẢI ABC?")

### ❓ Câu 1: Tại sao em lại chọn kiến trúc Multi-Agent (LangGraph) mà không dùng 1 Chain RAG đơn giản hay ReAct Agent duy nhất?

* **Trả lời (Why & Trade-off):**
  * **Vấn đề của Single Chain/ReAct Agent:** Khi cho 1 LLM xử lý tất cả (vừa kiểm tra an toàn, vừa tìm nguyên nhân, vừa đưa ra lời khuyên dinh dưỡng), Prompt sẽ bị quá tải (Prompt Bloat), LLM dễ bị **Hallucination** và rất khó kiểm soát chốt chặn an toàn y tế.
  * **Giải pháp Multi-Agent (LangGraph):** Em áp dụng nguyên lý **Phân tách trách nhiệm (Separation of Concerns)**:
    * `Triage Agent` đứng đầu làm chốt chặn an toàn (Guardrail).
    * `Supervisor Agent` đóng vai trò định tuyến.
    * Các Sub-agents (`Factor`, `Harm`, `Suggestion`) chuyên biệt hóa prompt và chạy song song qua LangGraph `Send API`.
  * **Kết quả:** Giúp dễ debug từng node, prompt ngắn và chuẩn xác hơn, đồng thời đảm bảo **100% câu hỏi kê đơn/cấp cứu bị chặn ngay tại Triage**.

---

### ❓ Câu 2: Tại sao em lại chọn mô hình Dual-LLM (Groq + Gemini 2.0 Flash) thay vì chỉ dùng 1 mô hình duy nhất như GPT-4o hay Claude 3.5?

* **Trả lời (Why & Trade-off):**
  * **Lý do:** Đây là bài toán trade-off giữa **Tốc độ (Latency)**, **Chi phí (Cost)** và **Context Window**:
    * **Supervisor / Router:** Cần phản hồi cực nhanh dưới 400ms để định tuyến $\rightarrow$ Em chọn **Groq (Llama 3.1 / gpt-oss)** nhờ kiến trúc LPU cho tốc độ 200-300 tokens/s.
    * **Trích xuất RAG / Sub-agents:** Cần xử lý văn bản tài liệu dài với giá rẻ $\rightarrow$ Em chọn **Gemini 2.0 Flash** vì giá token cực kỳ rẻ ($0.10/1M tokens) và context window 1M tokens.
  * **So sánh với giải pháp dùng 1 model (VD: GPT-4o):** Nếu dùng GPT-4o cho toàn bộ flow, chi phí API sẽ cao gấp 4-5 lần và latency bước routing sẽ bị kéo dài lên 1.2s-1.5s.
  * **Kết quả:** Giảm **~35% độ trễ tổng thể** và tiết kiệm **~40% chi phí token**.

---

### ❓ Câu 3: Tại sao lại kết hợp Hybrid Retrieval (Vector DB + Web Search) mà không chỉ dùng RAG nội bộ hoặc chỉ dùng Web Search?

* **Trả lời (Why & Trade-off):**
  * **Nếu chỉ dùng RAG nội bộ:** Dữ liệu chuẩn y khoa nhưng bị giới hạn trong các tệp PDF đã nạp, không cập nhật được các nghiên cứu/tin tức mới nhất.
  * **Nếu chỉ dùng Web Search:** Dữ liệu trên mạng rất nhiễu, chứa nhiều thông tin sai lệch hoặc quảng cáo thuốc không kiểm chứng.
  * **Giải pháp Hybrid:** 
    1. Ưu tiên tra cứu CSDL chuẩn y khoa từ **Qdrant Vector DB** (`BAAI/bge-m3` embedding).
    2. Bổ sung thông tin thời gian thực từ **SearXNG + Crawl4AI**.
    3. Dùng **Jina AI Reranker** để chấm điểm và lọc bỏ 80% nhiễu từ trang web trước khi đưa vào LLM.
  * **Kết quả:** Vừa đảm bảo tính chính xác y khoa, vừa có thông tin mới nhất kèm trích dẫn nguồn rõ ràng.

---

### ❓ Câu 4: Tại sao chọn BAAI/bge-m3 và Qdrant local mà không dùng OpenAI Embeddings và Pinecone/Weaviate Cloud?

* **Trả lời (Why & Trade-off):**
  * **BGE-M3:** Hỗ trợ đa ngôn ngữ (đặc biệt tốt với tiếng Việt y khoa) và hỗ trợ cả Dense + Sparse retrieval. Chạy local không tốn chi phí API embedding.
  * **Qdrant local:** Chạy Docker cục bộ với chỉ mục **HNSW**, thời gian query chỉ từ **10ms - 30ms**, không bị phụ thuộc vào băng thông mạng hay chi phí hàng tháng của Cloud Vector DB.

---

## 📌 PHẦN 3: GIẢI THÍCH CON SỐ KẾT QUẢ (METRICS & SUY LUẬN)

### ❓ Câu 5: Em giải thích con số "sub-2.5s retrieval speed" được tính toán như thế nào?

* **Trả lời (Latency Breakdown):**
  * Em phân rã tổng thời gian 2.5s thành các bước bất đồng bộ:
    1. **Vector Search (Qdrant + bge-m3 local):** ~300ms
    2. **Web Search (SearXNG Docker):** ~450ms
    3. **Jina Reranker API:** ~500ms
    4. **Web Scraper (Crawl4AI Async Top-3):** ~1,000ms (chạy song song)
  * Nhờ dùng `asyncio.gather()` để chạy Vector Search và Web Search song song, tổng thời gian retrieval chỉ bằng thời gian của nhánh dài nhất (~2.0s) + thời gian xử lý (~200ms) = **~2.2s (< 2.5s)**.

---

### ❓ Câu 6: Con số "12s timeout controls" và "99.9% reliability" có ý nghĩa gì và em giải quyết bài toán sập/treo như thế nào?

* **Trả lời (Troubleshooting Story):**
  * **Vấn đề:** Khi cào web hoặc gọi API rerank, nếu socket bị treo vĩnh viễn (Silent Drop trên Windows), Python Event Loop sẽ bị kẹt, làm đứng toàn bộ Server.
  * **Giải pháp:** Em bọc các I/O task trong `asyncio.wait_for(..., timeout=12.0)`. Nếu quá 12s, hệ thống chủ động ngắt task, log warning và kích hoạt **Graceful Degradation (Tự điều chỉnh giáng cấp)**:
    * Mức 1: Nếu cào web bị timeout $\rightarrow$ Dùng ngay đoạn tóm tắt (snippet) có sẵn của SearXNG.
    * Mức 2: Nếu Web search sập $\rightarrow$ Dùng dữ liệu RAG nội bộ Qdrant.
    * Mức 3: Nếu cả 2 cùng lỗi $\rightarrow$ Trả về câu trả lời tri thức chung từ LLM kèm lời khuyên bác sĩ.
  * **Kết quả:** Triệt tiêu 100% lỗi đứng server (Deadlock) và đảm bảo **99.9% request của người dùng luôn nhận được kết quả**.

---

## 📌 PHẦN 4: KỊCH BẢN TRẢ LỜI THEO PHƯƠNG PHÁP STAR (SITUATIONAL QUESTIONS)

### 🎯 Tình huống: "Hãy kể về một khó khăn kỹ thuật lớn nhất em gặp phải trong dự án này và cách em giải quyết?"

* **Situation (Bối cảnh):** Khi tích hợp công cụ cào dữ liệu web Crawl4AI và Jina Reranker vào hệ thống Multi-Agent, em gặp sự cố Server Uvicorn thỉnh thoảng bị kẹt cứng (hang) không phản hồi.
* **Task (Nhiệm vụ):** Phải tìm ra nguyên nhân gốc rễ (Root Cause) và khắc phục triệt để mà không được làm sập luồng làm việc của các Agent.
* **Action (Hành động):** 
  1. Đọc log và phát hiện lỗi do socket kết nối không ngắt khi mạng chập chờn, khiến Event Loop của Python bị phong tỏa.
  2. Áp dụng cơ chế **Timeout Control** với `asyncio.wait_for` khống chế hạn mức 10-12s.
  3. Xây dựng chiến lược **Fallback 3 cấp độ** để khi một công cụ bị timeout, pipeline vẫn tiếp tục chạy bằng dữ liệu dự phòng.
* **Result (Kết quả):** Hệ thống hoạt động ổn định 100%, không còn bị đơ vô hạn và tỉ lệ phản hồi thành công đạt 99.9%.

---

## 💡 LỜI KHUYÊN KHI ĐI PHỎNG VẤN:
1. **Luôn bắt đầu bằng Lý do kinh doanh / Kỹ thuật (Why):** Đừng chỉ nói *"Em dùng LangGraph vì nó hot"*, hãy nói *"Em dùng LangGraph vì cần quản lý State phức tạp và phân chia chốt chặn an toàn y tế"*.
2. **Thừa nhận Trade-off:** Không có công nghệ nào hoàn hảo. Khi khen Gemini Flash rẻ, hãy thừa nhận Groq nhanh hơn cho bước Routing. Điều này chứng minh bạn có tư duy Senior.
