# UC-016: llm multi provide

**Feature ID**: `UC-016`
**Version**: 3.0.0
**Date**: 24/07/2026
**Input**: 

---

## Actor
- Hệ thống

## Trigger
1. Người dùng gửi câu hỏi đến hệ thống

## Preconditions


## Main Flow
1. Người dùng gửi câu hỏi đến hệ thống.
2. Hệ thống gửi câu hỏi qua Triage Agent (Tác nhân Sàng lọc/Phân loại) để kiểm tra mức độ an toàn. -> sử dụng Gemini 2.0 Flash
3. Triage Agent xác nhận câu hỏi an toàn và chuyển tiếp đến Supervisor Agent. 
4. Supervisor Agent phân chia task song song cho 3 Agent con: -> sử dụng gpt-oss-20b
    - Factor Agent (Tác nhân xác định các yếu tố góp phần gây ra bệnh tiểu đường)
    - Suggestion Agent (Tác nhân cung cấp các đề xuất cụ thể, có thể thực hiện được liên quan đến bệnh tiểu đường)
    - Harm Agent (Tác nhân mô tả các tác hại và ảnh hưởng tiêu cực do bệnh tiểu đường gây ra)
5. Mỗi Agent con sử dụng LLM (prompt_system) để tạo tối đa 2 truy vấn con, kích hoạt tool phù hợp (Web Search hoặc RAG) để thu thập thông tin lần lượt với mỗi truy vấn. -> sử dụng Gemini 2.0 Flash
6. Sau khi nhận kết quả từ tool, mỗi Agent con sử dụng LLM trích xuất các ý chính ngắn gọn đúng với chuyên môn của nó. -> sử dụng Gemini 2.0 Flash
7. Hệ thống tổng hợp kết quả từ 3 Agent con (kèm metadata source, được định nghĩa trong state của agent đó) và truyền vào ou node (đã định nghĩa trong model) để Response Agent sử dụng. 
8. Response Agent sử dụng StateOutput của mỗi node (đã định nghĩa trong model) này để tạo câu trả lời cuối cùng và trả về cho người dùng. -> sử dụng gpt-oss-20b
