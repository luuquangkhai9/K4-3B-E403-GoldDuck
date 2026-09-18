# Báo cáo tích hợp hệ thống GoldDuck

## Nhiệm vụ 1 — Agent điều phối và mindmap tài liệu

Đã triển khai workflow một agent có giới hạn trong `app/agent/`, API `/api/chat`, UI nhận câu hỏi nguyên bản, chuẩn hóa topic, truy xuất tài liệu, thẩm định bằng evidence, kiểm tra metadata/ID/scope và dựng cây Day → tên file. Các endpoint cũ vẫn tương thích. Có hỗ trợ context cho câu tiếp nối và fallback phân biệt nguồn chưa thẩm định với đề xuất học đã thẩm định.

Kiểm tra trước tích hợp nhánh:

- 158 kiểm thử Python: qua.
- 15 kiểm tra giao diện Node: qua.
- 9 tình huống HTTP thật trong `scripts/verify_agent.py`: qua. Bao gồm câu hỏi Transformers nguyên văn, câu tiếp nối, tài liệu trong Day01, QA thường, mindmap Day01–03, chủ đề ngoài kho và lỗi phạm vi. Các lần gọi model/rerank thành công; đối chiếu nguồn với chỉ mục và mở ảnh trang thật.
- Headless Chrome: câu hỏi nguyên văn nhận cây Day/tên file, mở nguồn của từng tài liệu, không có lỗi JavaScript. Lượt cuối dùng fallback thực tế vì credit LLM đã hết; status `partial` và vai trò `candidate`, không trình bày nguồn chưa thẩm định như tài liệu bắt buộc học.

Báo cáo đầy đủ và ảnh tại `data/verification/` (được bỏ qua bởi Git). Kiểm tra API nhỏ xác nhận HTTP 429, code `credit_balance_exhausted`, type `insufficient_quota`. Đây là giới hạn tài khoản bên ngoài, không phải lỗi trong mã; không thay key/model hoặc che giấu tình trạng này. Cần bổ sung credit để tiếp tục thẩm định bằng LLM thật.

Danh sách tài liệu tìm được không được khẳng định bao phủ toàn khóa học. Metadata/ID được kiểm tra bằng mã; chất lượng ý nghĩa cần đánh giá bằng tập chuẩn. Chưa bật multiagent hoặc xây index tóm tắt tài liệu.

## Nhiệm vụ 2 — Đánh giá và tích hợp tainangtre

Đã merge `origin/tainangtre` tại `2d8c346` vào `quangkhai`. Giải quyết bốn conflict API, schema, JavaScript và chỉ mục; giữ toàn bộ 2.604 slide thay vì chấp nhận chỉ mục rỗng từ nhánh nguồn.

Giữ trải nghiệm hỏi lại/gợi ý của nhánh nguồn, thay quy tắc câu dưới 15 ký tự và gợi ý Transformer/Attention gán cứng bằng policy offline và tiêu đề có nguồn thật, đúng phạm vi Day. Chủ đề ngắn rõ nghĩa vẫn được xử lý. Chọn/nhập chủ đề làm rõ giữ nguyên câu hỏi, ý định mindmap tài liệu và phạm vi lúc hỏi. Thiếu khớp từ vựng không tự động được coi là thiếu bằng chứng ngữ nghĩa. Từ chối trả lời tách biệt với gợi ý xem tiếp; nguồn gợi ý mở được trong viewer.

- 167 kiểm thử Python và 19 kiểm tra UI: qua.
- Ba luồng HTTP thật (hỏi lại, abstention qua ask/chat), gợi ý scoped và mở trang PDF thật: qua, không gọi LLM.
- Sửa lỗi click gửi truyền event vào chuỗi và context cũ bị giữ lại sau câu hỏi mới.

LLM thật vẫn hết credit như ghi ở nhiệm vụ 1. Các ca thẩm định LLM được kiểm tra bằng fixture; không ghi nhận chúng là đánh giá ngữ nghĩa trên toàn khóa học.

## Nhiệm vụ 3 — Tích hợp vào main

Chưa thực hiện; sẽ giữ README của main và chuyển prototype vào `codebase/` theo cấu trúc nộp bài.
