# HAX Toolkit (Microsoft) — 18 nguyên tắc tương tác người–AI, bản dùng cho hackathon

Nguồn: **Microsoft HAX Toolkit** — https://www.microsoft.com/en-us/haxtoolkit/ · thư viện mẫu và ví dụ: https://www.microsoft.com/en-us/haxtoolkit/library/ · bài gốc: Amershi et al., *Guidelines for Human-AI Interaction*, CHI 2019. Tóm lược tiếng Việt do BTC viết lại; mỗi nguyên tắc kèm **câu hỏi tự kiểm** và **ví dụ trong khoá** để nhóm chọn ≥4 nguyên tắc cho spec §4b (`02-guide.md` §2.4) và chỉ đúng chỗ áp dụng trong prototype.

Bộ HAX gồm bốn phần, dùng theo thứ tự:

| Phần | Là gì | Dùng khi |
|---|---|---|
| **Guidelines** (18 nguyên tắc dưới đây) | Nguyên tắc thiết kế theo 4 giai đoạn tương tác | §2.4 chọn nguyên tắc; §2.7 tự soát |
| **Design Library** (patterns + examples) | Mỗi nguyên tắc có các *pattern* (cách làm) và ví dụ sản phẩm thật | Khi đã chọn nguyên tắc, tra pattern để biết cụ thể làm gì trên giao diện |
| **Workbook** | Bảng giúp team quyết nguyên tắc nào ưu tiên cho tính năng của mình | §2.4, họp nhóm 15 phút |
| **Playbook** | Bộ câu hỏi về hệ thống ngôn ngữ tự nhiên → sinh danh sách kịch bản lỗi cần test | §2.5 kịch bản rủi ro (github.com/microsoft/HAXPlaybook) |

---

## Giai đoạn 1 · Ban đầu — trước/khi người dùng bắt đầu

**G1 · Làm rõ hệ thống làm được gì.** Người dùng hiểu AI giúp được việc gì.
- Tự kiểm: câu đầu tiên người dùng thấy có nói đúng phạm vi không? Có ví dụ input mẫu không?
- Trong khoá: tutor VLearn mở đầu bằng cả đoạn văn — ai đọc? Bot Discord được tag thì trả lời được loại câu nào?

**G2 · Làm rõ nó làm tốt đến đâu.** Người dùng biết AI hay sai ở đâu, độ tin cậy ra sao.
- Tự kiểm: có nói "trả lời dựa trên tài liệu buổi X; ngoài đó mình sẽ nói rõ" không? Có chỉ báo độ chắc?
- Trong khoá: 28% câu trả lời tutor không trích dẫn — người học có biết câu nào đáng tin hơn?

## Giai đoạn 2 · Trong tương tác

**G3 · Đưa dịch vụ đúng thời điểm.** Hành động/ngắt lời dựa trên việc người dùng đang làm.
- Tự kiểm: gợi ý xuất hiện lúc người dùng cần hay lúc đang tập trung?

**G4 · Hiện thông tin đúng ngữ cảnh.** Thông tin liên quan tới việc và môi trường hiện tại.
- Trong khoá: học viên bôi đen trang 6 thì câu trả lời phải bám trang 6, không lan sang cả chương.

**G5 · Hợp chuẩn mực xã hội.** Giọng, cách xưng hô, mức trang trọng hợp với người dùng và bối cảnh.
- Trong khoá: học viên gõ "cái chi dợ" — tutor trả lời giọng gì? Bot gọi tên học viên có phù hợp không?

**G6 · Giảm thiên kiến xã hội.** Ngôn ngữ/hành vi không củng cố định kiến, không thiên vị nhóm nào.

## Giai đoạn 3 · Khi sai — hoặc không chắc

**G7 · Gọi dễ dàng.** Người dùng gọi AI khi cần chỉ bằng một thao tác.

**G8 · Gạt bỏ dễ dàng.** Bỏ qua gợi ý/câu trả lời không phù hợp mà không bị chặn flow.
- Tự kiểm: bỏ qua có mất gì không? Có phải đóng modal, xác nhận nhiều bước?

**G9 · Sửa dễ dàng.** Chỉnh, tinh chỉnh, khôi phục ngay trên kết quả.
- Trong khoá: học viên hỏi lại/sửa câu hỏi có được giữ ngữ cảnh không? Sửa một câu trong storyboard có phải tạo lại cả video?

**G10 · Thu hẹp phạm vi khi nghi ngờ.** Không chắc thì hỏi lại một câu, hoặc trả lời kèm giới hạn — không làm liều. *(Bắt buộc với mọi nhóm.)*
- Tự kiểm: input mơ hồ → hệ thống làm gì? Có ba đường: hỏi lại / đoán có báo / từ chối kèm hướng đi?

**G11 · Giải thích vì sao.** Người dùng hiểu được lý do AI làm điều vừa làm.
- Trong khoá: "vì đoạn bạn chọn ở trang 6 nói về X" — giải thích gắn với hành động tiếp theo; trích dẫn `[trang N]` là một dạng G11.

## Giai đoạn 4 · Theo thời gian

**G12 · Nhớ tương tác gần.** Giữ bộ nhớ ngắn hạn, cho phép người dùng tham chiếu "cái vừa nãy".

**G13 · Học từ hành vi người dùng.** Cá nhân hoá theo hành động thật của họ.

**G14 · Cập nhật và thích ứng thận trọng.** Không đổi hành vi đột ngột gây mất phương hướng.

**G15 · Khuyến khích phản hồi chi tiết.** Cho người dùng nói rõ họ thích/không thích gì ở kết quả — không chỉ 👍/👎.
- Trong khoá: chỉ 1,3% lượt tutor có rating — vì sao? Rating đặt ở đâu, hỏi gì?

**G16 · Nói rõ hậu quả hành động của người dùng.** Người dùng biết hành động của mình ảnh hưởng AI ra sao (ví dụ: "bạn ẩn gợi ý này → sẽ ít gợi ý loại này hơn").

**G17 · Kiểm soát toàn cục.** Người dùng bật/tắt, cấu hình cách AI theo dõi và hành xử.

**G18 · Thông báo khi thay đổi.** Báo khi AI thêm/đổi năng lực.

---

## Cách dùng trong 3 buổi

1. **§2.4:** chọn ≥1 trong G1–G2, **G10 bắt buộc**, ≥1 trong G8/G9/G11, tuỳ chọn thêm. Với mỗi nguyên tắc, viết một dòng trong spec §4b: *nguyên tắc → chỗ áp dụng cụ thể trong prototype (màn hình/thông điệp/hành vi) → kiểm bằng case nào trong golden set*.
2. **§2.5:** chạy HAX Playbook (hoặc tự trả lời bộ câu hỏi của nó) để sinh kịch bản lỗi cho hệ thống ngôn ngữ tự nhiên: input mơ hồ, ngoài phạm vi, đổi chủ đề, người dùng phản đối kết quả, hệ thống không chắc.
3. **§2.7 tự soát:** với từng nguyên tắc đã chọn, mở Design Library xem pattern tương ứng để chắc "áp dụng" không chỉ là một câu trong spec.
4. **§4.2 (bonus validation):** khi quan sát người thử, ghi lại vi phạm G8/G9/G10 — đó là nguồn thay đổi tốt nhất cho changelog.
