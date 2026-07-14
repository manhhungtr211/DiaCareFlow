# UC-000-web-tool: Tìm kiếm và trích xuất nội dung web (Search & Scrape)

## Metadata
- **ID:** UC-000-web-tool
- **Status:** draft
- **Owner:** <Tên của bạn>
- **Last updated:** 2026-07-14

## Actor
- **Người dùng**: Người có nhu cầu hỏi thông tin thực tế.

## Trigger
- Người dùng gửi một câu hỏi hoặc từ khóa cần tìm kiếm.

## Preconditions
1. Đã tích hợp thành công API của công cụ tìm kiếm XNG Search (hoặc đã host thông qua Docker).
2. Công cụ Crawl4ai đã được cài đặt và sẵn sàng hoạt động.
3. Đã cấu hình sẵn danh sách các tên miền y khoa/khoa học uy tín (host_name config).

## Main Flow
1. Người dùng đưa ra một câu hỏi hoặc từ khóa cần tìm kiếm.
2. Hệ thống kích hoạt công cụ XNG Search để tìm kiếm câu hỏi trên web.
3. Hệ thống nhận trả về danh sách các URL (lấy 5 URL đầu tiên).
4. Hệ thống tiến hành chấm điểm và ranking 5 URL này dựa trên tổng hợp các yếu tố: độ uy tín tên miền, path_boost (độ sâu URL), tần suất (freq) và đánh giá jina (Xem chi tiết công thức ở mục Notes).
5. Hệ thống chuẩn hóa điểm (ép min 0, max 5), sort giảm dần và giữ lại top 3 URL tốt nhất.
6. Hệ thống sử dụng webscraper (Crawl4ai) để lấy nội dung chi tiết từ 3 URL top đầu.
7. Hệ thống tổng hợp nội dung đã trích xuất và trả về kết quả cho người dùng.

## Alternative Flows
- **3a. XNG Search không tìm thấy URL nào phù hợp:** Hệ thống bỏ qua các bước sau và trả về thông báo "Không tìm thấy thông tin trên web cho câu hỏi này".

## Exceptions
- **E1. API XNG Search bị lỗi hoặc timeout:** Hệ thống dừng xử lý, trả về thông báo lỗi "Công cụ tìm kiếm đang tạm gián đoạn, vui lòng thử lại sau".
- **E2. Crawl4ai không lấy được nội dung từ một URL cụ thể (bị chặn bot, lỗi 404...):** Hệ thống bỏ qua URL đó, log lỗi lại và tiếp tục scrape URL tiếp theo trong danh sách top.

## Acceptance Criteria
### AC-1: Luồng trích xuất thành công (Happy Path)
Given: Người dùng đặt câu hỏi hợp lệ và XNG Search trả về 5 URL hợp lệ.
When: Hệ thống thực hiện quá trình tìm kiếm và ranking.
Then: Crawl4ai trích xuất thành công nội dung từ 3 URL có điểm cao nhất.
And: Hệ thống trả về kết quả tổng hợp cho người dùng.

### AC-2: Ranking - Ưu tiên tên miền uy tín
Given: URL A nằm trong danh sách tên miền uy tín cấu hình sẵn và URL B thì không.
When: Hệ thống tính điểm ranking ở Bước 4.
Then: Điểm multiplier của URL A phải là 2.
And: URL A phải có tổng điểm cao hơn URL B (nếu các chỉ số khác tương đương).

### AC-3: Ranking - Tính điểm Path Boost (Độ sâu URL)
Given: URL A có độ sâu 1 và URL B có độ sâu 2 cùng chung tiền tố.
When: Hệ thống tính điểm path_boost.
Then: Điểm decayed_boost của độ sâu 1 là 0.8^0 (1.0).
And: Điểm decayed_boost của độ sâu 2 là 0.8^1 (0.8).

### AC-4: Xử lý khi không có kết quả từ XNG Search
Given: Người dùng đặt câu hỏi vô nghĩa hoặc quá hẹp.
When: XNG Search trả về 0 URL.
Then: Trả về thông báo "Không tìm thấy thông tin".
And: Không kích hoạt tính toán ranking hay gọi dịch vụ Crawl4ai.

### AC-5: Xử lý khi 1 URL trong Top 3 không thể scrape
Given: Quá trình ranking chọn ra Top 3 URL (A, B, C).
When: Crawl4ai trích xuất thành công A, C nhưng B bị lỗi truy cập/chặn bot.
Then: Hệ thống vẫn trả về nội dung của A và C.
And: Không làm crash hệ thống vì URL B bị lỗi.

## Notes
**Quy tắc thuật toán Ranking (Áp dụng cho Bước 4 & 5):**
Tổng điểm của một URL được tổng hợp từ các thành phần sau, sau đó ép min = 0 và max = 5:
- **host_name:** Tính điểm dựa vào danh sách tên miền uy tín. Công thức: `tần suất xuất hiện * multiplier * trọng số`. (Nếu URL nằm trong file config tên miền uy tín, `multiplier = 2`).
- **path_boost:** Sử dụng regex lấy đuôi URL, tách theo từng độ sâu. Công thức: Tổng các độ sâu của `(prefix_freq * decayed_boost) * trọng số`. 
  - *Default decayed_boost:* Độ sâu 1 = 0.8^0; Độ sâu 2 = 0.8^1...
- **freq:** Sử dụng `item.weight` từ kết quả searchXNG * `freq_factor` (trọng số freq).
- **jina:** Sử dụng đánh giá jina * `jina_factor`.

**Kiến trúc:**
- Hiện tại chỉ viết tool riêng lẻ để gọi XNG và Crawl4ai, **chưa** tích hợp vào luồng của Agent.

## History
- v1 (2026-07-14, <Hùng>): Initial draft.
- v2 (2026-07-14, Refactored): Thêm thuật toán ranking vào Notes, bổ sung AC-2 và AC-3 để test luồng tính điểm.