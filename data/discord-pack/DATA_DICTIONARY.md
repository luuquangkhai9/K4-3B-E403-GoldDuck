# Data Dictionary — `k4_messages.csv`

Nguồn: hai server Discord khoá 4, crawl bằng bot (chỉ kênh public được chọn; tin đã xoá/sửa sau khi crawl không có). Xuất 15/09/2026, tin từ 12/09 06:57 đến 14/09 23:54 (giờ VN). 1.092 dòng = 1.092 tin nhắn.

| Cột | Kiểu | Ý nghĩa | Ghi chú |
|---|---|---|---|
| `msg_id` | `M#####` | Mã tin nhắn, đã mã hoá | Dùng để dẫn nguồn trong spec/golden set thay vì dán nguyên văn |
| `guild` | `K4-L2-3` / `K4-L3-4` | Server nào | Hai server tương ứng hai nhóm lớp của khoá 4 |
| `channel` | `channel_01`–`channel_12` | Kênh/luồng, đã mã hoá | Không có tên kênh. Mã kênh nhất quán trong toàn file |
| `author` | `D####` hoặc `BOT` | Người viết, đã mã hoá | Một người = một mã trong toàn file. `BOT` là bot "Trợ lý" của chương trình. Mod/TA/BTC cũng là `D####`, không phân biệt được với học viên |
| `is_bot` | bool | Tin do bot viết | 313 True |
| `msg_type` | `message` / `reply` | Tin thường hay tin trả lời | Tin hệ thống và lệnh slash đã bị loại |
| `created_at_vn` | `YYYY-MM-DD HH:MM` | Thời điểm gửi, giờ VN, làm tròn phút | |
| `reply_to` | `M#####` hoặc rỗng | Tin được trả lời | Rỗng nếu tin gốc không nằm trong pack |
| `mentions_bot` | bool | Tin có tag bot | Câu hỏi gửi cho bot |
| `n_attachments` | int | Số file đính kèm | Nội dung file không có trong pack |
| `n_chars` | int | Độ dài nội dung sau khi mask | |
| `content` | text | Nội dung tin, đã mask | Xem nhãn bên dưới |

## Nhãn ẩn danh trong `content`

| Nhãn | Thay cho |
|---|---|
| `[HV]` | Tên người (họ tên, tên gọi, username, tên hiển thị) |
| `[@D####]` / `[@BOT]` / `[@user]` | Tag người (mention); `[@user]` khi người đó không có trong pack |
| `[@role]` / `[#channel]` | Tag vai trò / tag kênh |
| `[MSSV]` | Mã sinh viên (đầy đủ hoặc 5 số cuối) |
| `[EMAIL]` / `[PHONE]` / `[ID]` / `[PASSCODE]` | Email, số điện thoại, ID số dài (Zoom, Discord), mật khẩu phòng họp |
| `[link:domain]` | Đường link, chỉ giữ tên miền |
| `[:emoji:]` | Emoji riêng của server |

Ưu tiên an toàn nên **có mask thừa**: một số từ Viết Hoa giữa câu trùng tên người (ví dụ "Ngân hàng", "Tài nguyên" ở vài chỗ) có thể thành `[HV]`. Đọc theo ngữ cảnh.

## Cách dữ liệu được ẩn danh

- Người → `D####` (xáo bằng hash, một người một mã); kênh → `channel_##`; tin → `M#####`; xoá username, tên hiển thị, ID Discord.
- Tên người trong nội dung → `[HV]` (họ tên, tên gọi, username, cả khi không dấu); mention → `[@D####]`; mã sinh viên → `[MSSV]`; email cá nhân → `[EMAIL]`; link Zoom và link tới tin nhắn/người trên Discord → `[link:…]`; mật khẩu phòng họp → `[PASSCODE]`. Link tài liệu (Drive, Docs, GitHub…) và email của chương trình giữ nguyên.
- Loại hẳn: tin hệ thống, lệnh slash rỗng, tin rỗng, 8 tin có hoàn cảnh cá nhân.
- Sau khi mask, toàn bộ file được quét lại tự động và rà thủ công; tên trong bản tin bot cũng đã thay bằng `[HV]`.

## Những gì KHÔNG có trong pack

- Tên kênh, tên vai trò, tên server thật.
- Tin nhắn riêng (DM), kênh private, thread không được chọn khi crawl.
- Tin hệ thống (vào server), lệnh slash không nội dung, tin rỗng/chỉ có file.
- 8 tin có hoàn cảnh cá nhân (xin nghỉ có lý do riêng, giấy tờ cá nhân) — đã loại hẳn.
- Bảng map mã ↔ người thật (không phát).

# `k4_daily_reports.md`

4 bản tin bot "Trợ lý" tự tổng hợp và đăng lên Discord (2 server × 2 ngày). Mỗi bản tin có: tiêu đề + số tin/kênh, đoạn tóm tắt, mục "Học viên đang hỏi gì", "Thảo luận học tập", "Learning Coach nên chú ý", và link tin nguồn (đã thay bằng `[link:discord.com]`). Tên người sau dấu "—" đã thành `[HV]`. Bản tin ở trạng thái `pending` (chưa gửi) không đưa vào.

Lỗi thật đang có trong bản tin — giữ nguyên để nhóm phân tích: chuỗi "nguồn tham chiếu" bị chèn vào giữa từ ("khi" → "nguồn tham chiếuhi"); tóm tắt dài bị cắt cụt; một số câu hỏi ghi "Đã có phản hồi, chưa xác nhận đã xử lý" không kiểm chứng được.
