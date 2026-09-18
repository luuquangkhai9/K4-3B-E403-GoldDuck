# Đề bài — "AI cho khoá AI Thực Chiến": 5 track, một khung chung

**Bối cảnh.** Khoá đang vận hành các sản phẩm AI nội bộ phục vụ ~1.000 học viên. Nhóm bạn là product team: chọn một track, tìm pain có bằng chứng, và build prototype **một tính năng**.

## Chọn 1 trong 5 track, rồi 1 đề trong track

Mỗi track mô tả các đề theo **cùng một khung mục** (người dùng · bối cảnh · bài toán gốc · lát cắt gợi ý · data & fixture · deliverable đầy đủ · demo · hard tests · rubric riêng · bonus · an toàn) để nhóm so sánh và chọn. Chi tiết và cách chọn: **`tracks/README.md`**.

| Track | Sản phẩm nền | Người dùng | Data trong repo | File |
|---|---|---|---|---|
| **A · VLearn Tutor** | AI tutor trong trang học VLearn — tối ưu cái đang chạy (A1) hoặc tính năng mới (A2) | Học viên; giảng viên | `data/vlearn-pack/` | `tracks/track-a-vlearn-tutor.md` |
| **B · Trợ lý Discord** | Bot "Trợ lý" + bản tin ngày đang chạy — tối ưu (B1) hoặc tính năng mới cho TA (B2) | Học viên; TA/Mod | `data/discord-pack/` + quan sát Discord | `tracks/track-b-discord-assistant.md` |
| **C · Lesson Studio** | Chuỗi sản xuất bài giảng/video VLearn — 5 đề C1–C5 (graph tri thức, QA kịch bản, nghiên cứu viết kịch bản, storyboard, phản hồi người học) | Studio team, lab coach/giảng viên; (C1, C5) người học | transcript/slide; Studio team có thể cấp thêm | `tracks/track-c-lesson-studio.md` |
| **D · Học tập thích ứng & tương tác** | Trải nghiệm học mới trên VLearn: lớp học mô phỏng đa tác tử (D1), học từ lỗi trước (D2), học bằng cách dạy (D3), hoặc đề mới cùng khung | Học viên | `data/vlearn-pack/` + cả lớp là user | `tracks/track-d-adaptive-interactive-learning.md` |
| **E · Làn mở** | Bất kỳ sản phẩm AI khác — **trong phạm vi AI20k**: phải phục vụ người trong khoá (học viên, giảng viên, TA, BTC, đội sản xuất) | Tự xác định, trong khoá | bất kỳ + khảo sát | `tracks/track-e-open-lane.md` |

Mọi track chấm chung `04-rubric.md`; rubric riêng trong từng đề chỉ để biết người làm thật quan tâm gì. Đề càng lớn (C, D), lát cắt càng phải nhỏ. E là làn cuối: chỉ chọn khi bài toán không nằm trong A–D.

## Data cấp cho mọi nhóm

Chatlog VLearn tutor × học viên đã ẩn danh + **6 transcript bài giảng bản sạch có mã đoạn để trích dẫn** + **2 bộ slide bài giảng bản hackathon** (xem `data/vlearn-pack/`). Với Trợ lý Học viên: có **`data/discord-pack/`** — 1.092 tin nhắn Discord khoá 4 giai đoạn onboarding (đã ẩn danh) + 4 bản tin ngày bot đang tự sinh (tính năng đang chạy thật, có lỗi thật để nhóm cải tiến). Pack chỉ 3 ngày và chỉ kênh public, nên nhóm **vẫn nên quan sát trực tiếp trong Discord khoá** để có evidence mới (đây cũng là một bài tập mining thực tế). **Cả lớp là người dùng thật** — nhóm có thể khảo sát 20 người ngay trong giờ nghỉ.

## Lát cắt = MỘT CÂU

> **một người dùng · một công việc · một quyết định AI · một kết quả**

## Ràng buộc chung

1. Build **prototype** (Sketch / Mock / Working) — mức nào cũng phải có **≥1 lời gọi AI chạy thật**. Không yêu cầu product hoàn chỉnh, không yêu cầu deploy.
2. Tự xác định **4 lớp chỗ khó** theo taxonomy — duyệt tại các mốc theo `04-rubric.md`:
   - ① **Nguồn sự thật** — chỗ nào AI bịa được? Không có căn cứ thì làm gì?
   - ② **Mơ hồ / thiếu thông tin** — input không đủ chắc: hỏi lại, đoán có báo, hay từ chối?
   - ③ **Ngoài phạm vi / thẩm quyền** — user đòi thứ không được phép làm, từ chối sao cho vẫn hữu ích?
   - ④ **Đặc thù domain** — sai cái gì thì user mất điểm, mất niềm tin, học sai kiến thức ngay?
3. Chỉ dùng data trong `data/` hoặc data giả tự sinh — không data thật của người thật ngoài pack đã rà. **Data được cấp thuộc quy định bảo mật** (xem README mục "Bảo mật dữ liệu được cung cấp") — không chia sẻ ra ngoài khoá, không commit vào repo nộp bài.

## 5 tiêu chí nghiệm thu bài toán *(áp cho MỌI hướng — kể cả tối ưu tính năng có sẵn)*

| # | Tiêu chí | Đạt khi |
|---|---|---|
| 1 | Pain cụ thể | Ai — đang làm gì — vướng đâu — hậu quả gì. "Mọi người thấy bất tiện" = không đạt |
| 2 | Bằng chứng | **(A)** khảo sát ≥20 người ngoài nhóm, ≥50% xác nhận, log toàn bộ câu hỏi + từng câu trả lời; và/hoặc **(B)** mining data: số đếm được + ≥5 ví dụ nguyên văn + phương pháp đếm kiểm lại được |
| 3 | Problem statement + impact | Không chữ AI; bảng impact ≥3 ứng viên (bao nhiêu người × tần suất × tốn gì mỗi lần) + lý do chọn + ứng viên đã loại |
| 4 | Lát cắt prototype được | Một câu theo đúng format trên, demo được trong 5 phút, build được trong thời gian sự kiện |
| 5 | User sẵn sàng thử *(khuyến khích — tính bonus)* | ≥2 người thật ngoài nhóm (tên cụ thể) đồng ý thử prototype trước demo |

*Canvas nháp nộp tại CP1; evidence và spec hoàn thiện dần, chốt tại hạn chốt spec (21:00 18/9, tại CP4).*
