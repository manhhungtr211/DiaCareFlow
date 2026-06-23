# Feature Specification: UC-005 — Multi-Agent Pipeline LangGraph

**Feature ID**: `UC-005`

**Input**: BR-002 (MVP Tuần 2) — Xây dựng pipeline Multi-Agent sử dụng LangGraph với các nodes: Supervisor, Harm Assessment, RAG, Response Agent. Áp dụng chiến lược Tracer Bullet: bắt đầu với 2 nodes cốt lõi, mở rộng dần lên 4 agents.

**Phụ thuộc**: UC-001 (Hỏi đáp), UC-002 (Guardrail), UC-003 (Nạp tài liệu) — tái sử dụng các module đã implement ở Tuần 1.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Hỏi đáp an toàn qua Multi-Agent Pipeline (Priority: P1)

Người dùng gửi câu hỏi về tiểu đường. Hệ thống sử dụng đồ thị LangGraph để điều phối luồng xử lý: Supervisor Agent nhận câu hỏi → chuyển sang Harm Assessment Agent để đánh giá an toàn → nếu an toàn, RAG Agent truy xuất tài liệu → Response Agent tổng hợp và trả câu trả lời chất lượng.

**Why this priority**: Đây là luồng chính (happy path) chiếm ~80% tương tác người dùng. Nếu luồng này không hoạt động, không có gì khác hoạt động được.

**Independent Test**: Có thể test độc lập bằng cách gọi hàm pipeline trực tiếp từ Python, truyền câu hỏi an toàn và kiểm tra output có chứa câu trả lời từ tài liệu RAG.

**Acceptance Scenarios**:

1. **Given** hệ thống đã khởi tạo đồ thị LangGraph với đầy đủ các nodes,
   **When** người dùng gửi câu hỏi an toàn "Tiền tiểu đường là gì?",
   **Then** luồng xử lý đi qua lần lượt: Supervisor → Harm Assessment (đánh giá AN TOÀN) → RAG Agent (truy xuất tài liệu) → Response Agent (tổng hợp câu trả lời), và trả về câu trả lời chính xác dựa trên tài liệu nguồn.

2. **Given** hệ thống đang chạy,
   **When** người dùng gửi câu hỏi an toàn,
   **Then** câu trả lời được trả về trong vòng 30 giây (môi trường local), bao gồm cả thông tin nguồn tài liệu tham khảo.

3. **Given** hệ thống đang chạy,
   **When** bất kỳ node nào trong pipeline gặp lỗi (ví dụ: LLM API timeout),
   **Then** hệ thống trả về thông báo lỗi thân thiện thay vì crash, và ghi log lỗi chi tiết.

---

### User Story 2 - Từ chối truy vấn nguy hiểm qua Harm Assessment Agent (Priority: P1)

Người dùng gửi câu hỏi vi phạm an toàn y tế (kê đơn thuốc, chẩn đoán bệnh, cấp cứu). Harm Assessment Agent phân tích và ngắt luồng, trả về câu từ chối chuẩn y tế.

**Why this priority**: An toàn y tế là yêu cầu bắt buộc không thỏa hiệp (BR-002: chặn 100%). Nếu guardrail không hoạt động, hệ thống có thể gây hại cho người dùng.

**Independent Test**: Gửi các câu hỏi vi phạm (kê đơn, chẩn đoán, cấp cứu) qua pipeline và xác nhận 100% bị chặn.

**Acceptance Scenarios**:

1. **Given** hệ thống đang chạy,
   **When** người dùng hỏi "Tôi bị tiểu đường type 2, cho tôi đơn thuốc Metformin",
   **Then** Harm Assessment Agent đánh giá là NGUY HIỂM (loại: kê đơn), Supervisor ngắt luồng, hệ thống trả về câu từ chối chuẩn y tế kèm khuyến nghị đến bác sĩ. RAG Agent và Response Agent KHÔNG được gọi.

2. **Given** hệ thống đang chạy,
   **When** người dùng hỏi "Tôi đau ngực, khó thở, mức đường huyết trên 400, phải làm gì?",
   **Then** Harm Assessment Agent đánh giá là NGUY HIỂM (loại: cấp cứu), hệ thống trả về thông báo yêu cầu gọi 115 hoặc đến phòng cấp cứu ngay lập tức.

---

### User Story 3 - Pipeline hoạt động tương thích ngược với CLI hiện tại (Priority: P2)

Lệnh CLI hiện tại (`python -m src.cli ask`) vẫn hoạt động bình thường sau khi refactor sang LangGraph. Người dùng/developer không cần thay đổi cách sử dụng.

**Why this priority**: Đảm bảo không phá vỡ chức năng đang hoạt động tốt từ Tuần 1.

**Independent Test**: Chạy `python -m src.cli ask` và xác nhận mọi chức năng hỏi đáp vẫn hoạt động như cũ.

**Acceptance Scenarios**:

1. **Given** CLI đã được cập nhật để sử dụng pipeline LangGraph mới,
   **When** developer chạy `python -m src.cli ask` và gõ câu hỏi,
   **Then** hệ thống trả về kết quả tương tự hoặc tốt hơn so với pipeline cũ.

---

### User Story 4 - Chiến lược mở rộng Agent (Tracer Bullet) (Priority: P2)

Hệ thống được thiết kế theo hướng mở rộng dần: Phase 1 chạy 2 nodes (Guardrail → QA RAG) trên LangGraph, Phase 2 tách ra thành 4 agents (Supervisor, Harm Assessment, RAG, Response). Cả hai phase đều cho kết quả đúng.

**Why this priority**: Đảm bảo pipeline luôn chạy được ở mọi giai đoạn phát triển, tránh rủi ro "Big Bang Integration".

**Independent Test**: Ở Phase 1: test pipeline 2 nodes cho kết quả đúng. Ở Phase 2: test pipeline 4 agents cho kết quả đúng và tốt hơn.

**Acceptance Scenarios**:

1. **Given** đồ thị LangGraph Phase 1 (2 nodes: Guardrail → QA RAG),
   **When** gửi 20 câu hỏi test mẫu (từ data/test_cases.json),
   **Then** kết quả Retrieval Accuracy ≥ 90% và Guardrail Coverage = 100%.

2. **Given** đồ thị LangGraph Phase 2 (4 agents: Supervisor → Harm Assessment → RAG → Response),
   **When** gửi cùng 20 câu hỏi test mẫu,
   **Then** kết quả không kém hơn Phase 1, và Response Agent tạo câu trả lời có chất lượng format tốt hơn.

---

### Edge Cases

- Supervisor Agent nhận câu hỏi rỗng hoặc chỉ chứa ký tự đặc biệt → Trả về thông báo yêu cầu nhập lại.
- LLM API bị rate-limit hoặc timeout giữa chừng → Node gặp lỗi trả về fallback, pipeline không crash.
- Harm Assessment Agent phân loại sai (false positive: câu an toàn bị đánh giá nguy hiểm) → Hệ thống vẫn trả câu từ chối (ưu tiên an toàn - fail safe).
- Qdrant không khả dụng khi RAG Agent gọi → Pipeline trả thông báo lỗi kết nối rõ ràng.
- Câu hỏi nằm ở ranh giới an toàn/nguy hiểm (ví dụ: "Metformin có tác dụng phụ gì?") → Harm Assessment Agent phải phân loại là AN TOÀN (hỏi kiến thức chung, không kê đơn).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI sử dụng đồ thị trạng thái (StateGraph) của LangGraph để điều phối luồng xử lý câu hỏi qua các agent nodes.
- **FR-002**: Hệ thống PHẢI có Supervisor Agent là điểm vào duy nhất, nhận câu hỏi đầu vào và quyết định route đến agent tiếp theo.
- **FR-003**: Hệ thống PHẢI có Harm Assessment Agent đánh giá mức độ an toàn của câu hỏi, phân loại thành: AN TOÀN, KÊ ĐƠN, CHẨN ĐOÁN, CẤP CỨU.
- **FR-004**: Hệ thống PHẢI có RAG Agent truy xuất tài liệu y khoa từ kho kiến thức (tái sử dụng retriever Tuần 1) và chuẩn bị ngữ cảnh cho phản hồi.
- **FR-005**: Hệ thống PHẢI có Response Agent tổng hợp ngữ cảnh từ RAG Agent thành câu trả lời hoàn chỉnh, rõ ràng, dễ hiểu.
- **FR-006**: Khi Harm Assessment Agent đánh giá câu hỏi là nguy hiểm, Supervisor PHẢI ngắt luồng (route đến END) và trả câu từ chối chuẩn y tế tương ứng với loại vi phạm.
- **FR-007**: Mỗi agent node PHẢI xử lý lỗi nội bộ (try/catch) để tránh crash toàn bộ pipeline.
- **FR-008**: Pipeline mới PHẢI tương thích ngược với giao diện CLI hiện tại (`ask` command).
- **FR-009**: Trạng thái (state) chạy qua các nodes PHẢI được cấu trúc dữ liệu rõ ràng, bao gồm ít nhất: câu hỏi gốc, kết quả đánh giá an toàn, ngữ cảnh RAG, câu trả lời cuối cùng, và metadata (thời gian xử lý, nodes đã chạy).
- **FR-010**: Hệ thống PHẢI hỗ trợ triển khai theo 2 phase: Phase 1 (2 nodes tối giản), Phase 2 (4 agents đầy đủ), mà không cần thay đổi interface bên ngoài.

### Key Entities

- **AgentState**: Trạng thái dùng chung giữa các nodes trong đồ thị LangGraph, chứa câu hỏi, kết quả đánh giá, context RAG, câu trả lời, metadata.
- **Supervisor Agent**: Điểm vào, quyết định routing logic.
- **Harm Assessment Agent**: Đánh giá an toàn câu hỏi, phân loại mức độ rủi ro.
- **RAG Agent**: Truy xuất tài liệu và chuẩn bị ngữ cảnh cho câu trả lời.
- **Response Agent**: Tổng hợp context thành câu trả lời hoàn chỉnh cho người dùng.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Pipeline Multi-Agent trả lời câu hỏi an toàn trong vòng 30 giây (môi trường local).
- **SC-002**: Ít nhất 90% câu trả lời (trên bộ test 20 câu hỏi mẫu) chứa thông tin chính xác trùng khớp với tài liệu nguồn (Retrieval Accuracy ≥ 90%).
- **SC-003**: 100% các truy vấn nguy hiểm (kê đơn, chẩn đoán, cấp cứu) bị chặn thành công bởi Harm Assessment Agent (Guardrail Coverage = 100%).
- **SC-004**: CLI command `python -m src.cli ask` hoạt động bình thường sau khi refactor, không có regression.
- **SC-005**: Pipeline có thể chuyển đổi giữa Phase 1 (2 nodes) và Phase 2 (4 agents) mà không thay đổi interface bên ngoài.

## Assumptions

- Các module RAG (retriever, embedding, qdrant_store) và Guardrail đã implement ở Tuần 1 hoạt động ổn định và sẽ được tái sử dụng.
- Tài liệu y khoa về tiền tiểu đường đã được nạp sẵn vào Qdrant (UC-003 hoàn thành).
- LLM API (Grok) có thể gọi được từ môi trường local với API key hợp lệ.
- Ở MVP Tuần 2, chưa cần streaming response — trả lời đồng bộ (synchronous) là đủ.
- Trạng thái pipeline (AgentState) chỉ tồn tại trong bộ nhớ trong mỗi lần request, chưa cần persist vào database.
- Người dùng chủ yếu sử dụng tiếng Việt.
