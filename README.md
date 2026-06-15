# DiaCareFlow
# BR-001: DiaCareFlow — Hỗ trợ bệnh tiểu đường 
## Goal 
- Hệ thống multi-agent Intelligent hỗ trợ bệnh tiểu đường cá nhân hóa
- Tìm kiếm RAG và truy xuất thông tin Web Search để cung cấp thông tin giáo dục sức khỏe dựa trên bằng chứng y khoa cục bộ và tìm kiểm trên web theo thời gian thực
- Tích hợp pipeline xử lý tài liệu (Parse PDF, tạo metadata, chia nhỏ tài liệu và tải lên Vector DB) cho phép người dùng bổ sung kiến thức riêng vào hệ thống.
- AI dự kiến: Supervisor Agent, Suggestion Agent, Harm Assessment Agent, Factor Analysis Agent, Response Agent.

- Hệ thống User: làm tính năng Đăng nhập/Đăng ký,lưu trữ lịch sử chat của người dùng.
- Tích hợp API End-to-End: nối luồng giao tiếp giữa Frontend và Backend 
- Deployment: triển khai (deploy) lên Cloud (AWS/GCP)
 
## Success Metrics
- Kỹ thuật: Real-time Streaming, trả lời dưới 30s. RAG phải truy xuất tài liệu y khoa đạt trên 90%
- Chỉ số an toàn: Phát hiện 100% các truy vấn nguy hiểm và đưa ra cảnh báo. Không kê đơn thuốc, không chẩn đoán bệnh

## In Scope (MVP - Tuần 1) 
- RAG PoC: Chạy script nạp PDF (Tiền tiểu đường) vào Qdrant và test độ chính xác truy xuất nội dung.
- Agent Testing: Viết Prompt y khoa cho 5 Agents; test logic và output của từng node LangGraph riêng biệt.
- Safety Guardrails: Chạy test case giả lập để kiểm chứng khả năng chặn 100% các truy vấn kê đơn hoặc cấp cứu.
- Static UI: Chỉnh sửa giao diện tĩnh (Next.js) sang branding y tế, chưa cần nối luồng API Backend.
 
## Out of Scope 
- Cá nhân hóa các đề xuất cải thiện lối sống để ngăn ngừa bệnh tiến triển (idea sau)