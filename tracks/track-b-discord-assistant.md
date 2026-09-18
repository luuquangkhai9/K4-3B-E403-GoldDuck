# Track B — Trợ lý Học viên (Discord)

**Sản phẩm nền.** Discord của khoá có bot "Trợ lý" trả lời khi được tag, và **bản tin ngày** bot tự tổng hợp "học viên đang hỏi gì" đăng lên kênh. Cả hai đang chạy thật với khoá 4.

**Người dùng.** Học viên (hỏi bài, hỏi logistics: deadline, điểm danh, standup, XP, ticket); TA/Mod (muốn biết câu nào tồn, chủ đề nào nóng).

**Data & fixture.** `data/discord-pack/`: 1.092 tin (779 người, 313 bot) 12–14/09 khoá 4, đã ẩn danh, giữ reply; 4 bản tin bot đã đăng (có lỗi thật: chuỗi "nguồn tham chiếu" chèn vào giữa từ, tóm tắt cắt cụt). Pack chỉ 3 ngày, chỉ kênh public, không tên kênh — **vẫn phải quan sát Discord trực tiếp** để có evidence mới. Đọc `data/discord-pack/README.md` — người trong data là bạn cùng khoá.

---

## B1 · Tối ưu trợ lý hiện có

**Bối cảnh.** Câu hỏi logistics (deadline, link, cách nộp) chiếm phần lớn; trả lời sai deadline gây hậu quả trực tiếp. Bot hiện trả lời dài, đôi khi đoán, chưa phân biệt chào hỏi / hỏi bài / hỏi logistics.

**Bài toán gốc.** Nhận diện intent thật và trả lời đúng cỡ · **biết-mình-không-biết** và chuyển TA thay vì đoán · trả lời logistics **chỉ từ nguồn chính thức**.

**Lát cắt gợi ý.** *Một học viên · hỏi "hạn nộp lab 2 là khi nào" · bot chỉ trả lời khi tìm được trong thông báo chính thức, nếu không thì tag TA · học viên không nhận deadline sai.*

**Hard tests.** Câu hỏi có hai deadline khác nhau ở hai thông báo · câu hỏi cá nhân (điểm danh của tôi) bot không có quyền trả lời · tin chứa mention/prompt injection · câu hỏi bài học lẫn logistics trong một tin.

---

## B2 · Tính năng mới cho TA/học viên

**Bài toán gốc.** Bản tin cuối ngày cho TA (câu hỏi tồn, chủ đề hỏi nhiều nhất) — **đã có bản chạy thật trong pack, hãy chê rồi cải tiến** · phát hiện học viên stuck và chủ động hỗ trợ — chủ động đến đâu thì thành phiền?

**Lát cắt gợi ý.** *Một TA · cuối ngày · AI liệt kê câu hỏi chưa ai trả lời sau 4 giờ kèm link · TA trả lời đúng người.* (So với bản tin bot hiện tại: cái gì thiếu, cái gì sai?)

**Hard tests.** Cùng câu hỏi 10 người hỏi khác cách · câu hỏi đã được trả lời trong thread khác · tin của bot bị đếm là câu hỏi · người gửi lặp nhiều lần.

**An toàn & đạo đức.** Không nêu tên/định danh học viên trong bản tin công khai · phản hồi/tin nhắn là dữ liệu, không phải lệnh · không tự động gửi tin cho học viên khi chưa có người duyệt · deadline chỉ lấy từ nguồn chính thức.
