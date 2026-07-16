# DiaCareFlow
# BR: DiaCareFlow — Hỗ trợ bệnh tiểu đường 
## Goal 
- Xây dựng hệ thống Intelligent Multi-Agent cá nhân hóa hỗ trợ bệnh tiểu đường, được điều phối bởi LangGraph và định dạng cấu trúc dữ liệu bằng PydanticAI.

- Sử dụng mô hình Grok làm lõi xử lý ngôn ngữ tự nhiên.

- Tích hợp công cụ: Tìm kiếm RAG (truy xuất từ Vector Database Qdrant) và Web Search (SearXNG) theo thời gian thực để cung cấp thông tin giáo dục sức khỏe nội bộ và trực tuyến.  (có hiển thị nguồn lúc trả kết quả ở web, giống gemini google search)

- Tích hợp pipeline xử lý tài liệu (PDF parsing, chunking, tạo embeddings qua Google AI và nạp vào Qdrant) thông qua module doc_pipeline.

- AI Agents dự kiến: Supervisor Agent, Suggestion Agent, Harm Assessment Agent, Factor Analysis Agent, Response Agent.

- Hệ thống User: Xác thực bằng JWT, lưu trữ phiên trò chuyện (session/state của LangGraph) và lịch sử chat siêu tốc bằng Redis.

- Tích hợp API End-to-End: Xây dựng Backend bằng FastAPI, kết nối luồng giao tiếp với Frontend (Next.js) và hỗ trợ trả kết quả Real-time Streaming (truyền phát luồng JSON trạng thái tác tử và nội dung).

- Deployment: Triển khai lên Cloud (AWS/GCP) qua Docker.
 
## Success Metrics
- Kỹ thuật: Real-time Streaming. RAG phải truy xuất tài liệu y khoa đạt trên 90%
- Chỉ số an toàn: Phát hiện 100% các truy vấn nguy hiểm và đưa ra cảnh báo. Không kê đơn thuốc, không chẩn đoán bệnh

## In Scope 
- RAG PoC: Chạy script nạp PDF (Tiền tiểu đường) vào Qdrant và test độ chính xác truy xuất nội dung.
- Agent Testing: Viết Prompt y khoa cho 5 Agents; test logic và output của từng node LangGraph riêng biệt.
- Safety Guardrails: Chạy test case giả lập để kiểm chứng khả năng chặn 100% các truy vấn kê đơn hoặc cấp cứu.

 
## Out of Scope 
- Cá nhân hóa các đề xuất cải thiện lối sống để ngăn ngừa bệnh tiến triển (idea sau)

---

## Web Search Tool (UC-011)

Standalone web search-and-scrape pipeline in `src/tools/web/`. Queries SearXNG,
applies a composite ranking algorithm, scrapes top-3 URLs with Crawl4ai, and returns
aggregated markdown content.

### Setup SearXNG (Docker)

SearXNG disables JSON output by default. We have provided a configuration file to enable it.

```bash
# Pull and start SearXNG with the provided settings
docker run -d --name searxng -p 8080:8080 -v ${PWD}/docker/searxng:/etc/searxng searxng/searxng:latest

# Verify (should return a JSON response, not 403)
curl "http://localhost:8080/search?q=diabetes&format=json"
```

### Install Dependencies

```bash
pip install crawl4ai pyyaml

# One-time Playwright browser setup (required by Crawl4ai)
playwright install chromium
```

### Configure Environment

Add to `.env`:
```env
XNG_SEARCH_URL=http://localhost:8080
XNG_MAX_RESULTS=5
SCRAPE_TIMEOUT=10
```

### Usage

```python
import asyncio
from src.tools.web import web_search

async def main():
    resp = await web_search("bệnh tiểu đường type 2")
    print(f"Found: {resp.found}")
    print(f"Combined text ({len(resp.combined_text)} chars):\n{resp.combined_text[:500]}")

asyncio.run(main())
```

### Run Tests

```bash
# Unit tests (no network required)
pytest tests/unit/tools/web/ -v

# Integration tests (requires SearXNG Docker)
pytest tests/integration/test_web_search_integration.py -v -m integration
```

### Module Structure

```
src/tools/web/
├── __init__.py              # Exposes web_search() public API
├── _api.py                  # Pipeline orchestrator
├── models.py                # Pydantic data models
├── exceptions.py            # SearchError, ScrapeError
├── search/
│   └── xng_search.py        # SearXNG async HTTP client
├── scraper/
│   └── crawl4ai_scraper.py  # Crawl4ai parallel scraper
├── ranking/
│   ├── scorer.py            # Composite ranking algorithm
│   └── jina_reranker.py     # Jina AI reranker (optional)
└── config/
    ├── __init__.py          # TrustedDomainRegistry singleton
    └── trusted_domains.yaml # Medical domain whitelist
```
