# Ví dụ Canvas 7 dòng (CP1)

Canvas nộp ở CP1 theo scaffold `02-guide.md` §1.5 — mỗi dòng một ý, cả canvas vừa một trang. Dưới đây là 3 bài của các nhóm khoá trước (đã ẩn tên, chỉnh nhẹ), kèm ghi chú vì sao đạt. Số liệu trong ví dụ viết dạng `XX/XXX` — nhóm bạn phải tự đếm trên `data/` của khoá này và ghi số thật.

## Mẫu trống — copy vào `canvas.md` của repo nhóm

| # | Dòng | Nội dung |
|---|---|---|
| 1 | Track + đề | |
| 2 | Job executor (ai · đang ở đâu · làm gì) | |
| 3 | Pain một câu (ai – đang làm gì – vướng đâu – hậu quả) | |
| 4 | 1–2 bằng chứng đầu (số + cách đếm + mã hội thoại/tin nhắn, hoặc khảo sát/phỏng vấn có số người) | |
| 5 | Lát cắt MỘT CÂU (1 user · 1 việc · 1 quyết định AI · 1 kết quả) | |
| 6 | AI tự làm đến đâu + 1 dòng lý do · ≥3 willing users ngoài nhóm | |
| 7 | Phân công có tên | |

Bằng chứng ở dòng 4 có thể đến từ **data pack** (đếm được, có mã trích dẫn) hoặc **khảo sát / phỏng vấn** (ghi số người hỏi, số người gặp vấn đề, quote ngắn) — tốt nhất là cả hai.

---

## Mẫu 1 · Track A — tối ưu tutor có sẵn

1. **Track + đề:** A · VLearn Tutor — trả lời có căn cứ từ tài liệu.
2. **Job executor:** Học viên đang đọc slide trong buổi học, vừa bôi đen một đoạn chưa hiểu.
3. **Pain:** Khi hỏi để làm rõ đoạn vừa bôi đen, học viên nhận câu trả lời không có trích dẫn hoặc trích dẫn sai; không biết tutor dựa vào đâu nên phải tự dò lại slide, mất thời gian và có thể học sai.
4. **Bằng chứng đầu:**
   - `XXX/X.XXX` phản hồi tutor có `citations` rỗng (`XX%`). *Cách đếm:* lọc `role = tutor` trong `tutor_turns.csv`, đếm `citations = []`. *Mã hội thoại minh hoạ:* `T0XXXX`, `T0XXXX`, `T0XXXX`.
   - Khảo sát nhanh `XX` học viên trong lớp: `XX/XX` nói "lần gần nhất hỏi tutor, không biết câu trả lời lấy từ trang nào".
5. **Lát cắt:** Học viên đang đọc slide · cần làm rõ đoạn vừa bôi đen · AI **chỉ trả lời khi truy xuất được đoạn nguồn phù hợp**, nếu không thì nói "chưa đủ căn cứ" và hỏi lại · kết quả là câu trả lời kèm mã trang/đoạn.
6. **AI tự làm đến đâu:** *Tự:* nhận đoạn bôi đen, truy xuất bài học, chọn đoạn nguồn, sinh câu trả lời kèm trang. *Không tự:* suy đoán khi không tìm được nguồn — phải nêu rõ chưa đủ căn cứ. *Lý do:* `XX%` phản hồi hiện không có citation; nội dung học tập không kiểm chứng được có thể làm học viên học sai. **Willing users (ngoài nhóm, đã hỏi và đồng ý):** `[Tên 1]`, `[Tên 2]`, `[Tên 3]`.
7. **Phân công:** `[Tên A]` — mining evidence, bảng đếm + mã hội thoại · `[Tên B]` — retrieval/prompt + tiêu chí "đủ căn cứ" · `[Tên C]` — prototype + AI call thật · `[Tên D]` — spec, golden set, demo · `[Tên E]` — user test, feedback log, changelog.

> **Vì sao đạt:** dòng 4 có *số, cách đếm, mã hội thoại* — TA kiểm được trong 2 phút; khảo sát bổ sung cho thấy pain là thật với người thật. Dòng 5 có đúng một quyết định AI (trả lời / không trả lời). Dòng 6 nói rõ AI *không* làm gì và vì sao. Dòng 7 mỗi việc một tên.

---

## Mẫu 2 · Track A/D — tính năng mới

1. **Track + đề:** A · VLearn — tính năng mới: *Learning Trace*, bản đồ ôn tập cá nhân sau mỗi buổi. *(Ý tưởng này cũng hợp track D — chọn một track khi nộp.)*
2. **Job executor:** Học viên vừa kết thúc một buổi học trên VLearn, đã có ≥1 lượt trao đổi với tutor trong buổi đó.
3. **Pain:** Sau buổi học, các câu hỏi và kiến thức đã tìm hiểu nằm rời rạc trong lịch sử chat; học viên không biết mình đã hỏi gì, phần nào chưa vững, nên ôn gì trước.
4. **Bằng chứng đầu:**
   - Data pack có `X.XXX` lượt hỏi–đáp của `XXX` học viên — đủ signal để khảo sát. Trường `misconceptions` rỗng `XX%`; chỉ `XX` lượt tutor đặt câu kiểm tra hiểu bài. *Nguồn:* `data/vlearn-pack/chatlog/DATA_DICTIONARY.md`, ghép theo `turn_id`.
   - Phỏng vấn `XX` học viên: `XX/XX` nói lần gần nhất muốn ôn lại thì "không biết bắt đầu từ đâu"; `XX/XX` mở lại toàn bộ slide thay vì phần mình đã hỏi.
5. **Lát cắt:** Học viên vừa xong buổi học · muốn biết nên ôn lại gì · AI phân tích lịch sử hỏi–đáp của buổi đó để quyết định chủ đề đã tìm hiểu và điểm có khả năng chưa vững · sinh note ngắn có căn cứ để học viên xem, xác nhận hoặc sửa.
6. **AI tự làm đến đâu:** *Có điều kiện:* tự sinh note khi đủ log và nguồn chính thức; khi signal yếu thì ghi "chưa đủ dữ liệu", **không kết luận học viên hổng kiến thức**. *Lý do:* suy luận sai làm học viên ôn sai trọng tâm và mất niềm tin — nên phải được xem căn cứ, xác nhận, sửa hoặc gạt bỏ. **Willing users:** `[Tên 1]`, `[Tên 2]`, `[Tên 3]`.
7. **Phân công:** `[Tên A]` — product lead, canvas/spec, system prompt, output contract · `[Tên B]` — data & evidence, mining, khảo sát · `[Tên C]` — golden set, quality bar, eval · `[Tên D]` — backend, gọi model, validator · `[Tên E]` — UI, 4 đường trải nghiệm, user test.

> **Vì sao đạt:** bằng chứng lấy từ *cái không có* trong data (trường rỗng, rất ít lượt kiểm tra hiểu bài) — cách mining khôn, rồi đối chiếu bằng phỏng vấn. Dòng 6 nói rõ hệ thống không được kết luận gì khi thiếu dữ liệu. Bản gốc dài gấp đôi — canvas không cần dài.

---

## Mẫu 3 · Track B — trợ lý Discord

1. **Track + đề:** B · Trợ lý Discord — trả lời câu hỏi tiện ích lặp lại.
2. **Job executor:** Học viên mới, tuần đầu, đang ở kênh chung, vừa gõ một câu hỏi về tiện ích (căn tin, thư viện, thẻ, wifi).
3. **Pain:** Câu hỏi bị trôi giữa tin nhắn khác, không ai trả lời hoặc trả lời sau vài giờ; học viên hỏi lại hoặc tự đi tìm, cùng một câu được hỏi nhiều lần.
4. **Bằng chứng đầu:**
   - Trong `discord-pack/k4_messages.csv`, `XX/X.XXX` tin là câu hỏi tiện ích (lọc từ khoá "căn tin | thư viện | thẻ | wifi | gửi xe" + dấu "?"); `XX` trong số đó không có reply trong 2 giờ. *Mã tin minh hoạ:* `D0XXX`, `D0XXX`, `D0XXX`.
   - Hỏi `XX` học viên trong lớp: `XX/XX` từng hỏi một câu tiện ích trên Discord mà không được trả lời; `XX/XX` cuối cùng đi hỏi trực tiếp coach.
5. **Lát cắt:** Học viên mới gõ câu hỏi tiện ích vào kênh chung · AI quyết định câu hỏi có khớp mục nào trong tài liệu nội quy/tiện ích không · nếu khớp thì trả lời kèm trích dẫn mục; nếu không thì nói "chưa có trong tài liệu" và tag người phụ trách.
6. **AI tự làm đến đâu:** *Tự* trả lời khi tìm được mục khớp; *không tự* suy đoán, *không tự* tạo event/poll thay người dùng. *Lý do:* thông tin sai về nội quy làm học viên vi phạm; tạo event thay mặt người khác là hành động không hoàn tác được. **Willing users:** `[Tên 1]`, `[Tên 2]`, `[Tên 3]`.
7. **Phân công:** `[Tên A]` — evidence + golden set · `[Tên B]` — prompt/retrieval · `[Tên C]` — bot + AI call · `[Tên D]` — spec + demo · `[Tên E]` — user test + changelog.

> **Vì sao đạt:** dòng 2 là *một vai đang làm một việc*, không phải "học viên nói chung". Dòng 4 đếm được trên Discord pack và có mã tin để TA mở ra xem. Dòng 5 chỉ có **một** việc (trả lời câu hỏi tiện ích) — không gộp thêm "gom nhóm đá bóng" dù ý tưởng ban đầu có; phần đó để backlog. Dòng 6 nói rõ AI không hành động thay người dùng.

---

*Chỉnh sửa từ bài nộp của các nhóm khoá trước, đã ẩn tên và thay số liệu bằng `XX`. Số thật do nhóm bạn tự đếm.*
