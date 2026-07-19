# UC-012: Xử lý câu hỏi người dùng qua hệ thống Multi-Agent

**Feature ID**: `UC-012`
**Input**: 

---

## Actor
- **Người dùng**: Người có nhu cầu tra cứu và hỏi đáp thông tin chuyên môn.

## Trigger
1. Người dùng gửi câu hỏi đến hệ thống

## Preconditions
1. Hệ thống đã cấu hình thành công các công cụ (RAG, SearXNG).
2. Các Agent (Triage, Supervisor, Factor, Suggestion, Harm Assessment, Response) đã được khởi tạo và cấu hình đúng role.

## Main Flow
1. Người dùng gửi câu hỏi đến hệ thống.
2. Hệ thống gửi câu hỏi qua Triage Agent (Tác nhân Sàng lọc/Phân loại) để kiểm tra mức độ an toàn.
3. Triage Agent xác nhận câu hỏi an toàn và chuyển tiếp đến Supervisor Agent.
4. Supervisor Agent phân chia task song song cho 3 Agent con: 
    - Factor Agent (Tác nhân phân tích nguyên nhân)
    - Suggestion Agent (Tác nhân đưa ra đề xuất giải pháp)
    - Harm Assessment Agent (Tác nhân đánh giá rủi ro)
5. Mỗi Agent con tự đánh giá và kích hoạt tool phù hợp (RAG, WebSearch hoặc cả 2) để thu thập thông tin.
6. Sau khi nhận kết quả từ tool, mỗi Agent con sử dụng LLM trích xuất các ý chính ngắn gọn đúng với chuyên môn của nó.
7. Hệ thống tổng hợp các câu trả lời từ 3 Agent con và truyền vào một State dùng chung.
8. Response Agent sử dụng State tổng hợp này để tạo câu trả lời cuối cùng và trả về cho người dùng.


## Alternative Flows
- **2a. Triage Agent phát hiện câu hỏi không an toàn:** Hệ thống bỏ qua bước 3 đến 7. Triage Agent gửi trực tiếp kết quả cảnh báo tới Response Agent để xuất câu trả lời từ chối cho người dùng.

## Acceptance Criteria
### AC-1: Trả lời câu hỏi hợp lệ thành công (Happy Path)
Given: Tài liệu y khoa đã được nạp và SearXNG hoạt động tốt.
When: Người dùng hỏi "Người tiền tiểu đường nên ăn gì?".
Then: Supervisor chia đều task cho 3 Agent chuyên môn.
And: Response Agent trả về lời khuyên dinh dưỡng dựa trên tài liệu y khoa và web.
And: Nội dung trả về tuyệt đối không tự sáng tạo ra thông tin không có trong tài liệu.

### AC-2: Triage chặn câu hỏi độc hại (Của Alternative Flow 2a)
Given: Hệ thống đã sẵn sàng.
When: Người dùng hỏi một câu hỏi vi phạm chính sách hoặc không an toàn.
Then: Triage Agent đánh dấu không an toàn.
And: Response Agent trả về câu cảnh báo ngay lập tức.
And: Không có bất kỳ Agent con hay Tool nào (RAG/SearXNG) bị kích hoạt để tránh tốn token.
## Notes
<!-- - **Context refactor:** UC này thay thế cho luồng kiến trúc cũ nhằm giải quyết tình trạng Agent bị quá tải ngữ cảnh và tốn kém token (Chi tiết triển khai kỹ thuật xem tại `design.md`). -->
- Giải thích vì sao thay đổi nằm ở `proposal.md`