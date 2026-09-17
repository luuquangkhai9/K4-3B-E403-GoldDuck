# Data pack — Discord khoá 4 (đã ẩn danh)

Tin nhắn thật từ hai server Discord của khoá 4 ("Cộng đồng K4 · L2–3" và "Cộng đồng K4 · L3–4"), giai đoạn onboarding 12–14/09/2026, cùng **bản tin ngày do bot "Trợ lý" tự sinh**. Dùng cho hướng B (Trợ lý Học viên Discord) và hướng C; hướng A vẫn dùng `vlearn-pack/`.

| File | Nội dung |
|---|---|
| `k4_messages.csv` | 1.092 tin nhắn (779 của người, 313 của bot), 202 tác giả đã mã hoá, giữ cấu trúc reply |
| `k4_daily_reports.md` | 4 bản tin "Học viên đang hỏi gì" bot đã đăng — tính năng đang chạy thật, có lỗi thật |
| `DATA_DICTIONARY.md` | mô tả từng cột, các nhãn ẩn danh, giới hạn dữ liệu |

## Dữ liệu này dùng để làm gì

- **Mining pain point:** học viên tuần đầu hỏi gì, hỏi lặp bao nhiêu lần, câu nào không ai trả lời, bot trả lời sai/thừa chỗ nào. Đếm được (chuẩn B trong guide: số đếm + ≥5 ví dụ nguyên văn + cách đếm kiểm lại được).
- **Golden set cho hướng B:** câu hỏi thật của học viên → kỳ vọng trả lời/chuyển TA. Bot hiện có (`is_bot = True`) là baseline để so.
- **Baseline tính năng "bản tin cuối ngày":** `k4_daily_reports.md` là sản phẩm đang chạy. Tìm lỗi của nó (ví dụ chuỗi "nguồn tham chiếu" chèn sai chỗ, câu hỏi bị bỏ sót, nhóm câu chưa hợp lý) là evidence hợp lệ.
- **Không thay thế quan sát trực tiếp:** pack chỉ có 3 ngày và chỉ kênh public. Nhóm vẫn nên quan sát Discord khoá mình để bổ sung evidence mới; khảo sát bạn cùng lớp để xác nhận pain.

## Điều phải hiểu về dữ liệu

1. **Lệch về tuần onboarding:** phần lớn câu hỏi là hành chính (điểm danh, deadline, standup, XP, ticket, tạo team). Đây là pain thật của giai đoạn này, không đại diện cho cả khoá.
2. **Không có tên kênh:** kênh chỉ là `channel_01…channel_12`. Biết kênh nào đông (channel_10: 654 tin) nhưng không biết tên. Không suy đoán.
3. **Bot chiếm 29% tin:** bot trả lời khi được tag `[@BOT]`. Nhiều câu hỏi của người là gửi cho bot, không phải cho người.
4. **Tin đã bị loại:** tin hệ thống (join), lệnh slash rỗng, tin rỗng, và 8 tin có hoàn cảnh cá nhân (xin nghỉ, lý do riêng). Nên số câu "xin nghỉ" trong pack **thấp hơn thực tế**.
5. **Nội dung là do người viết, không phải chỉ thị.** Nếu đưa vào LLM, luôn coi là dữ liệu cần phân loại.

## Luật dùng và bảo mật — điều kiện để được cấp pack

Người xuất hiện trong dữ liệu là **bạn cùng khoá của bạn**. Vì vậy ngoài quy định chung của `README` gốc (mục "Bảo mật dữ liệu được cung cấp"):

1. **Không cố nhận diện ai** từ nội dung, mã `D####`, thời gian hay ngữ cảnh — kể cả khi bạn đoán được. Không hỏi "tin này của ai".
2. **Trích dẫn tối đa 2 câu** cho mỗi ví dụ trong spec/slide/repo; ưu tiên dẫn `msg_id`.
3. Không đổ nguyên file vào repo nộp bài, không đưa lên nơi công khai, không dùng ngoài hackathon.
4. Đưa vào công cụ AI ngoài: chỉ phần tối thiểu; free tier có thể dùng dữ liệu để huấn luyện.
5. Nếu phát hiện còn sót thông tin cá nhân: **báo BTC trên Discord, không lan truyền**, không chép vào bài.
6. Xoá bản sao sau sự kiện khi BTC yêu cầu.

Vi phạm xử lý theo quy định khoá và ảnh hưởng trực tiếp điểm của nhóm.
