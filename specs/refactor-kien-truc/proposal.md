# Đề xuất: Refactor kiến trúc sang Multi-Agent cho tính năng Web Tool

## Background (Bối cảnh)
Hiện tại, công cụ RAG, tìm kiếm và trích xuất web đang được gộp chung, coi nó như là một node của Agent. Điều này dẫn đến việc Agent bị quá tải ngữ cảnh và độ chính xác của câu trả lời không cao. Để AI hoạt động tốt nhất, chúng ta cần tái cấu trúc theo hướng chia nhỏ task: mỗi Agent chỉ làm đúng một việc duy nhất và thiết kế lại tool chuẩn theo định dạng Agent.

## Goal (Mục tiêu)
Nâng cấp độ chính xác của câu trả lời bằng cách áp dụng kiến trúc Multi-Agent (chia nhỏ Agent cho luồng Search và Scrape).

## Success Metrics (Thước đo thành công)
- Tỷ lệ sinh câu trả lời chính xác (dựa trên tập test characterization) đạt 100% so với dữ liệu chuẩn.
- Không làm thay đổi/phá vỡ luồng người dùng (User Flow) hiện tại.

## In Scope (Phạm vi công việc)
- Tách Agent để phân chia công việc
- Định nghĩa các tool RAG, XNG SSearch, Crawl4ai cho các Agent

## Out of Scope (Ngoài phạm vi - Không làm)
- Không thay đổi thuật toán tính điểm Ranking URL (đã chốt ở UC-000-web-tool).
- Không sửa đổi UI/UX của người dùng.
- Không tích hợp thêm tool nào khác ngoài XNG Search và Crawl4ai trong lần refactor này.