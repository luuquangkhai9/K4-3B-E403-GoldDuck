# Data pack — Mini Hackathon AI · Batch 04

Hai bộ dữ liệu thật của chương trình, đã ẩn danh, cấp riêng cho hackathon. Dùng để **tìm bằng chứng** (mining), **chọn bài toán** có số liệu, **dựng golden set** và làm context cho prototype. Không có bộ nào là "đề bài" — nhóm tự đặt câu hỏi rồi đi tìm trong data.

| Bộ | Cho hướng | Nội dung | Quy mô | Đọc trước |
|---|---|---|---|---|
| `vlearn-pack/` | **A** (VLearn Tutor) · C · **D** · E | Log chat học viên × AI tutor + transcript bài giảng + slide | 13.494 lượt hỏi-đáp · 6 transcript · 2 slide · 36 MB | [`vlearn-pack/README.md`](vlearn-pack/README.md) |
| `discord-pack/` | **B** (Trợ lý Discord) · E | Tin nhắn Discord khoá 4 + bản tin bot tự sinh | 1.092 tin nhắn · 4 bản tin · 0,4 MB | [`discord-pack/README.md`](discord-pack/README.md) |
| `studio-pack/` | **C** (Lesson Studio · C3–C5) | Tài liệu sản xuất của Studio team: mẫu kịch bản chung, kịch bản + video thật đã phát hành, lời đọc có mốc từng từ, hồ sơ nguồn mẫu, góp ý mẫu | 3 gói · ~13 MB (gần hết là một video 4 phút) | [`studio-pack/README.md`](studio-pack/README.md) |

Track C (Lesson Studio) dùng transcript/slide làm tài liệu thô, và `studio-pack/` cho C3–C5 (không phải dữ liệu người học, không có gì cần ẩn danh); track D dùng cả chatlog lẫn transcript/slide; track E (làn mở) dùng bộ nào cũng được. Chi tiết theo đề: `tracks/`.

## 1. `vlearn-pack/` — VLearn AI tutor

Sản phẩm: AI tutor trên nền tảng VLearn, học viên bôi đen đoạn slide/tài liệu rồi hỏi; tutor trả lời có (hoặc không) trích dẫn trang.

| File | Là gì | Con số |
|---|---|---|
| `chatlog/tutor_turns.csv` | Hội thoại thật học viên ↔ tutor, **mỗi dòng 1 lượt hỏi-đáp** (câu hỏi + câu trả lời) | **13.494 lượt**, 1.617 học viên, 29 bài giảng có tên, 22/07 → 15/09/2026; `cohort_hint = K4` = 3.097 lượt của chính khoá này (448 học viên, từ 09/09) |
| `chatlog/DATA_DICTIONARY.md` | Mô tả 19 cột: ngữ cảnh, câu hỏi/trả lời, nước đi sư phạm, trích dẫn, rating, latency, cờ câu mẫu | Đọc trước khi mining |
| `transcript/transcript-01…06-clean.md` | 6 transcript bài giảng đã làm sạch, ~700 đoạn có mã `[Txx-NNN]` để trích dẫn | ~610 KB text |
| `slides/d1-…pdf`, `d2-…pdf` | 2 bộ slide bài giảng bản hackathon (Day 1 AI & LLM Foundation · Day 2 Xác định bài toán), 29 trang/bộ | dùng làm context/grounding |

Vài con số để bắt đầu hỏi (tự kiểm lại trên data): **22,7% câu hỏi là câu mẫu bấm sẵn** (`is_preset`); 28% câu trả lời **không trích dẫn** tài liệu; chỉ **1,3%** lượt có rating (92 up / 85 down); `understanding_level` gần rỗng; tutor gần như **không hỏi ngược** (`ask_probing_question` 28 lượt, `review_concept` 90%); ngày 30/07 có 2.579 lượt (một hoạt động trên lớp) chi phối thống kê; tutor **gọi tên học viên** ở đầu ~4.200 câu trả lời (đã mask thành `Chào [HV]`) — một quyết định thiết kế đáng bàn.

Ẩn danh: học viên → `S####`, lượt → `T#####`; tên người (kể cả tên học viên tutor gọi, tên giảng viên trong slide) → `[HV]`; email/MSSV/link/số dài → nhãn; 3 lượt bị loại (2 cờ an toàn của hệ thống, 1 từ khoá nhạy cảm). Nhãn `[REDACTED_*]` có sẵn của nền tảng giữ nguyên. Chi tiết cách ẩn danh: `vlearn-pack/chatlog/DATA_DICTIONARY.md`.

## 2. `discord-pack/` — Discord khoá 4

Sản phẩm: cộng đồng Discord của khoá (hai server "K4 · L2–3" và "K4 · L3–4") và **bot "Trợ lý"** trả lời khi được tag, kèm **bản tin ngày** bot tự tổng hợp "học viên đang hỏi gì".

| File | Là gì | Con số |
|---|---|---|
| `discord-pack/k4_messages.csv` | Tin nhắn thật, 1 dòng 1 tin, giữ cấu trúc reply | **1.092 tin**: 779 của người, 313 của bot; 202 tác giả; 508 tin là reply; 307 tin tag bot; 12–14/09/2026 (tuần onboarding) |
| `discord-pack/k4_daily_reports.md` | 4 bản tin bot đã đăng — tính năng đang chạy thật, **có lỗi thật** (chuỗi "nguồn tham chiếu" chèn vào giữa từ, tóm tắt cắt cụt) | baseline để chê và cải tiến |
| `discord-pack/DATA_DICTIONARY.md` | 12 cột + bảng nhãn ẩn danh (`[HV]`, `[@D####]`, `[MSSV]`, `[link:domain]`…) | Đọc trước khi mining |

Giới hạn phải nhớ: chỉ 3 ngày, chỉ kênh public; **không có tên kênh** (`channel_01…12`); lệch về câu hỏi hành chính tuần đầu (điểm danh, deadline, standup, XP, ticket, lập team); 8 tin hoàn cảnh cá nhân đã bị loại nên số câu "xin nghỉ" thấp hơn thực tế; Mod/TA và học viên đều là `D####`, không phân biệt được.

Ẩn danh: tên người → `[HV]`, người → `D####`, kênh → `channel_##`, xoá username/link/ID/email/mã sinh viên/passcode. Người trong data là **bạn cùng khoá** — quy tắc riêng ở `discord-pack/README.md`.

## 3. Cách dùng đúng chuẩn evidence (guide §1.3)

- Đọc **30–50 mẫu trước** để biết loại pattern, rồi mới định nghĩa cách đếm; ghi quy tắc đếm để người khác kiểm lại được.
- Bằng chứng mining = **số đếm + ≥5 ví dụ nguyên văn + phương pháp**. Dẫn `msg_id` / `turn_id` / `[Txx-NNN]` thay vì dán đoạn dài.
- Golden set ≥20 case, ≥10 case lấy hoặc phát triển từ data thật (chatlog **hoặc** Discord, tuỳ hướng).
- Nội dung do học viên viết là **dữ liệu, không phải chỉ thị** — đã thấy câu kiểu "bỏ qua hướng dẫn trước đó" trong chatlog. Đưa vào LLM thì nói rõ đây là data cần phân loại.

## 4. Luật chung cho cả hai bộ

Theo `README.md` của repo, mục "Bảo mật dữ liệu được cung cấp": chỉ dùng trong hackathon · không chia sẻ ra ngoài khoá · không commit nguyên pack vào repo nộp bài (trích ngắn, dẫn mã) · đưa vào công cụ AI ngoài thì tối thiểu · không cố suy ngược danh tính · xoá bản sao sau sự kiện khi BTC yêu cầu. Riêng `discord-pack/`: **không đoán "tin này của ai"**, trích tối đa 2 câu mỗi ví dụ, phát hiện sót thông tin cá nhân thì báo BTC.
