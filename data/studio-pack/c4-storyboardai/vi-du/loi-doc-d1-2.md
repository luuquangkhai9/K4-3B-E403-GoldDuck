# Lời đọc — Mô hình ngôn ngữ lớn sinh văn bản như thế nào (42 câu)

Đây là phần lời đọc đã chốt của một video thật, **đã bỏ toàn bộ mô tả hình**.
Nhiệm vụ của bạn là dựng lại phần hình cho từng câu.

| Câu | Phần | Bắt đầu | Kết thúc | Lời đọc |
|---|---|---|---|---|
| 1 | 1 | 00:00.0 | 00:05.6 | Khi một trợ lý hội thoại trả lời, các bạn thường thấy chữ xuất hiện dần trên màn hình. |
| 2 | 1 | 00:05.6 | 00:12.2 | Trong bài này, mình xét cách mô hình tạo từng mảnh văn bản rồi dùng phần vừa có để viết tiếp. |
| 3 | 1 | 00:12.2 | 00:16.7 | Hãy nhìn câu chưa hoàn thành trên màn hình: tôi mang ô vì trời. |
| 4 | 1 | 00:16.7 | 00:24.1 | Điều cần hiểu cuối video là mô hình chọn mảnh tiếp theo như thế nào và vì sao câu nghe hợp lý vẫn có thể sai. |
| 5 | 2 | 00:24.1 | 00:29.9 | Trước tiên, văn bản được chia thành những mảnh nhỏ để xử lý, gọi là token. |
| 6 | 2 | 00:29.9 | 00:37.1 | Một mảnh có thể là cả một từ, chỉ một phần của từ hoặc một dấu câu, tùy cách chia của mô hình. |
| 7 | 2 | 00:37.1 | 00:44.0 | Tên gọi mảnh văn bản giúp mình dễ hình dung, còn token được chia ở đâu là do bộ tách quyết định. |
| 8 | 2 | 00:44.0 | 00:50.5 | Đặc biệt với tiếng Việt, các bạn không nên đếm khoảng trắng rồi mặc định mỗi tiếng là đúng một token. |
| 9 | 2 | 00:50.5 | 00:56.9 | Mỗi mảnh được chuyển thành mã số, rồi thành một dãy số để mô hình thực hiện phép tính. |
| 10 | 2 | 00:56.9 | 01:03.7 | Qua nhiều bước tính toán, những dãy số này kết hợp thông tin từ phần văn bản mà mô hình được phép dùng. |
| 11 | 2 | 01:03.7 | 01:10.5 | Hãy nhìn vào ô trống sau chữ trời và thử đoán xem những cách nối tiếp nào nghe có vẻ phù hợp. |
| 12 | 3 | 01:10.5 | 01:15.7 | Từ phần câu đã có, mô hình tính khả năng xuất hiện của từng mảnh có thể nối tiếp. |
| 13 | 3 | 01:15.7 | 01:22.5 | Bảng minh họa có các lựa chọn mưa, nắng, lạnh và một nhóm gom những cách nối khác. |
| 14 | 3 | 01:22.5 | 01:29.9 | Mình đặt khả năng của mưa cao hơn để dựng ví dụ dễ hình dung; các tỷ lệ này không được lấy từ một mô hình thật. |
| 15 | 3 | 01:29.9 | 01:36.5 | Các phần trăm trong bảng nói về mảnh văn bản có thể nối tiếp, không đo xem trời thật sự đang mưa hay không. |
| 16 | 3 | 01:36.5 | 01:42.5 | Mô hình thật có nhiều mảnh để chọn hơn, và một từ trên thẻ có thể cần tách thành nhiều mảnh. |
| 17 | 3 | 01:42.5 | 01:47.9 | Sau khi có bảng khả năng, hệ thống dùng một quy tắc để chọn ra mảnh tiếp theo. |
| 18 | 3 | 01:47.9 | 01:52.0 | Một cách là luôn chọn mảnh có khả năng cao nhất trong bảng. |
| 19 | 3 | 01:52.0 | 01:59.6 | Cách khác là chọn theo các mức khả năng ấy, nên những mảnh ít khả năng hơn vẫn có thể được chọn. |
| 20 | 3 | 01:59.6 | 02:04.9 | Giả sử lần này chọn mưa, hệ thống nối mảnh ấy vào cuối câu đang viết. |
| 21 | 3 | 02:04.9 | 02:10.7 | Lần dự đoán sau sẽ dùng cả chữ mưa vừa thêm, vì nó đã trở thành một phần của câu. |
| 22 | 3 | 02:10.7 | 02:17.0 | Do đó, bảng khả năng phải được tính lại ở mỗi bước, thay vì dùng mãi bảng của bước đầu. |
| 23 | 3 | 02:17.0 | 02:21.7 | Các bước dự đoán, chọn và nối lặp lại cho đến khi gặp điều kiện dừng. |
| 24 | 3 | 02:21.7 | 02:27.7 | Hệ thống có thể dừng khi có tín hiệu kết thúc, hoặc khi câu trả lời đã chạm mức độ dài cho phép. |
| 25 | 3 | 02:27.7 | 02:34.8 | Vì vậy, câu trả lời có thể bị cắt khi chưa viết xong, chỉ vì đã hết phần độ dài được cấp. |
| 26 | 4 | 02:34.8 | 02:39.2 | Bây giờ, hãy giữ nguyên phần đầu câu và thử một cách nối khác. |
| 27 | 4 | 02:39.2 | 02:45.2 | Một nhánh viết tôi mang ô vì trời mưa, còn nhánh kia viết tôi mang ô vì trời đang mưa. |
| 28 | 4 | 02:45.2 | 02:50.3 | Khi một bước chọn khác đi, phần câu làm căn cứ cho bước sau cũng thay đổi. |
| 29 | 4 | 02:50.3 | 02:56.4 | Cách chọn vẫn dựa vào phần câu đã có và quy tắc của hệ thống, chứ không ghép chữ tùy tiện. |
| 30 | 4 | 02:56.4 | 03:02.4 | Kết quả còn phụ thuộc vào mô hình được dùng, yêu cầu của bạn và các thông tin phần mềm gửi kèm. |
| 31 | 4 | 03:02.4 | 03:11.0 | Muốn so hai lần thử, hãy kiểm tra cả câu hỏi, thông tin gửi kèm, mô hình và cách chọn mảnh có giống nhau không. |
| 32 | 5 | 03:11.0 | 03:16.6 | Bây giờ thay câu mang ô bằng yêu cầu cho biết hạn nộp bài của lớp vào tuần tới. |
| 33 | 5 | 03:16.6 | 03:24.1 | Nếu ứng dụng không cung cấp lịch chính xác, mô hình vẫn có thể tạo ra một câu trả lời nghe rất tự nhiên về ngày và giờ. |
| 34 | 5 | 03:24.1 | 03:30.2 | Chọn được một chuỗi chữ hợp lý không có nghĩa hệ thống đã mở lịch của lớp để kiểm tra hạn nộp. |
| 35 | 5 | 03:30.2 | 03:35.8 | Thông tin mô hình đã học có thể thiếu hoặc đã cũ, nhất là với lịch riêng của một lớp. |
| 36 | 5 | 03:35.8 | 03:43.0 | Ứng dụng có thể gửi lịch lớp cho mô hình, hoặc dùng công cụ tra lịch rồi cung cấp kết quả tra cứu. |
| 37 | 5 | 03:43.0 | 03:50.0 | Ngay cả khi có nguồn, chúng ta vẫn cần kiểm tra câu trả lời có bám đúng dữ liệu được cung cấp hay không. |
| 38 | 6 | 03:50.0 | 03:55.8 | Vì sao cùng một câu hỏi có thể được trả lời bằng hai cách diễn đạt khác nhau mà vẫn giữ gần như cùng ý? |
| 39 | 6 | 03:55.8 | 04:00.8 | *(dừng 5 giây)* |
| 40 | 6 | 04:00.8 | 04:07.8 | Vì có nhiều cách nối các mảnh văn bản phù hợp với câu hỏi, và quy tắc lựa chọn có thể tạo ra các cách nối khác nhau. |
| 41 | 6 | 04:07.8 | 04:13.2 | Muốn biết câu trả lời có đúng sự thật, chúng ta vẫn cần đối chiếu với nguồn đáng tin. |
| 42 | 6 | 04:13.2 | 04:21.6 | Hãy nhớ dự đoán, chọn, nối rồi lặp, trước khi sang video Transformer để xem các phần xử lý bên trong. |

## Các phần

| Phần | Tên |
|---|---|
| 1 | Mở đầu — chữ xuất hiện từ đâu |
| 2 | Token — đơn vị mô hình xử lý |
| 3 | Dự đoán, chọn, nối rồi lặp |
| 4 | Một đầu vào, nhiều cách diễn đạt |
| 5 | Vì sao câu trôi chảy vẫn có thể sai |
| 6 | Câu hỏi và kết luận |
