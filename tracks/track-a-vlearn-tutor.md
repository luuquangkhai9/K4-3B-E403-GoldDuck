# Track A — VLearn Tutor

**Sản phẩm nền.** VLearn là nền tảng học tập thích ứng của khoá. Trong trang học có AI tutor: học viên bôi đen một đoạn tài liệu/slide rồi hỏi; tutor trả lời kèm trích dẫn `[trang N]`, chọn một "nước đi sư phạm" (review_concept, give_example, give_hint…), học viên có thể bấm rating up/down.

**Người dùng.** Học viên đang học trong trang (hỏi bài, ôn trước quiz, xem lại buổi nghỉ); giảng viên/TA muốn biết lớp đang kẹt ở đâu.

**Data & fixture.** `data/vlearn-pack/`: chatlog **13.494 lượt hỏi-đáp thật** (22/07 → 15/09; 1.617 học viên; `cohort_hint = K4` là 3.097 lượt của chính khoá này từ 09/09), 6 transcript có mã đoạn, 2 slide. Đọc `data/vlearn-pack/chatlog/DATA_DICTIONARY.md` trước: 28% câu trả lời không trích dẫn; 1,3% có rating; `understanding_level` gần rỗng; tutor gần như không hỏi ngược (`ask_probing_question` 28/13.494); 22,7% câu hỏi là câu mẫu bấm sẵn (`is_preset`) — tách ra trước khi kết luận "học viên hỏi gì".

---

## A1 · Tối ưu AI tutor hiện có

**Bối cảnh.** Tutor đã chạy thật với hàng nghìn lượt; log cho thấy chỗ trả lời không căn cứ, trả lời không đúng cỡ, không hỏi lại khi câu hỏi mơ hồ, không biết mình không biết.

**Bài toán gốc.** Mining chatlog để tìm một điểm tutor đang làm chưa tốt — có số đếm và ví dụ nguyên văn — chọn **một** điểm và cải thiện đến nơi đến chốn, đo được trước/sau trên golden set lấy từ chatlog thật.

**Lát cắt gợi ý.** *Một học viên · hỏi một câu ngoài phạm vi tài liệu đang mở · tutor nhận ra không có căn cứ và nói rõ thay vì bịa · học viên biết phải tìm ở đâu.* Hoặc: *học viên bấm câu mẫu "giải thích đoạn bôi đen" · tutor hỏi lại một câu để biết mức hiểu · trả lời đúng cỡ.*

**Hard tests.** Câu hỏi không liên quan tài liệu · đoạn bôi đen quá ngắn/vô nghĩa · học viên dán code hoặc chỉ dẫn "bỏ qua hướng dẫn trước đó" · câu hỏi đúng nhưng tài liệu sai/thiếu.

---

## A2 · Tính năng AI mới trên VLearn

**Bài toán gốc.** Một tính năng mới cho học viên hoặc giảng viên, xuất phát từ pain có trong data. Ví dụ *cảm cỡ* (không phải danh sách bắt buộc): kiểm tra hiểu thật cuối buổi · trải nghiệm học online cho người nghỉ buổi · bản đồ lỗ hổng của lớp cho giảng viên từ signal/chatlog.

**Lát cắt gợi ý.** *Một giảng viên · sau buổi học · AI gom câu hỏi của lớp theo trang thành 5 chỗ khó nhất kèm ví dụ · giảng viên chọn chỗ để ôn buổi sau.*

**Hard tests.** Lớp hỏi ít (data thưa) · câu hỏi mẫu chiếm đa số · hai trang cùng nói một khái niệm · signal nhiễu (một người hỏi 20 lần).

**An toàn & đạo đức (cả A1, A2).** Không lộ ai hỏi gì cho người khác · không đưa dữ liệu học viên ra ngoài pack · tutor không được "đoán chắc" khi không có căn cứ · giảng viên là người quyết định nội dung dạy.
