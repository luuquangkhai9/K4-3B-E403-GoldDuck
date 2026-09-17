# C3 · ScriptScout — Agent tự tìm tài liệu và viết kịch bản video có dẫn nguồn

**Tóm tắt: đưa vào một chủ đề, nhận về kịch bản video mà mỗi câu đều truy được về nguồn.**

> Đề chính thức và cách cắt lát cho hackathon: `tracks/track-c-lesson-studio.md`. Thư mục này là tài liệu đi kèm.

---

## Bối cảnh

Muốn làm một video bài giảng thì trước hết phải có kịch bản, tức toàn bộ lời sẽ đọc trong video. Hiện nay
người biên soạn phải tự đọc tài liệu, tự tra cứu trên mạng rồi tự viết. Việc này mất nhiều ngày, và khi
đưa cho người khác duyệt thì không ai kiểm được câu nào lấy từ đâu, vì danh sách nguồn chỉ được liệt kê ở
cuối tài liệu. Thiếu tư liệu thì người viết dễ đưa vào những con số hoặc ví dụ không có thật. Riêng chủ đề
AI còn thay đổi từng tháng, nên một thông tin đúng lúc viết có thể đã cũ khi video lên sóng. Các công cụ
"nghiên cứu sâu" hiện có viết được báo cáo dài, nhưng báo cáo để đọc bằng mắt khác hẳn kịch bản để đọc
thành lời, chia theo từng cảnh và chỉ ra được từng câu dựa trên nguồn nào.

## Bài toán

Hãy xây dựng một agent chỉ cần nhận bốn thông tin: chủ đề, mục tiêu bài học, người học là ai và video dài
bao lâu — không đưa sẵn tài liệu nào. Agent tự đi tìm tài liệu trên mạng, tự đánh giá tài liệu nào đáng
tin, rồi viết kịch bản.

Kết quả trả về gồm hai phần. Phần một là **hồ sơ tài liệu**: mỗi nguồn ghi rõ lấy ở đâu, ai viết, đăng
ngày nào, đáng tin ở mức nào và vì sao, kèm đoạn trích được dùng làm bằng chứng; chỗ nào các nguồn nói
khác nhau thì phải nêu ra. Phần hai là **kịch bản** viết đúng mẫu, trong đó mỗi câu có chứa thông tin, con
số hay ví dụ thực tế đều bấm được để xem đoạn tài liệu gốc. Người duyệt xem hồ sơ tài liệu trước, bỏ nguồn
nào thấy không ổn hoặc thêm nguồn của mình, rồi agent mới viết. Khi một nguồn bị bỏ, chỉ những câu dựa vào
nguồn đó được viết lại, phần còn lại giữ nguyên.

Chỗ khó nhất của đề này là phân biệt **"tìm được tài liệu"** với **"tài liệu đáng tin"**. Hệ thống phải nói
rõ vì sao tin một nguồn, dựa trên những tiêu chí công bố trước. Số liệu quan trọng cần ít nhất hai nguồn
độc lập xác nhận, nếu không thì phải đánh dấu là chưa kiểm chứng. Kịch bản phải là văn nói, đọc lên nghe
tự nhiên, mỗi ý một cảnh, chứ không phải bản tóm tắt báo cáo. Ngoài các yêu cầu đó, đội thi tự chọn công
cụ tìm kiếm, model AI và cách dựng agent.

> **PHẠM VI:** đội thi chỉ cần làm ra kịch bản, **không phải dựng thành video**. Đội nào giải xong bài
> toán chính mà còn thời gian thì có thể dựng luôn một video từ chính kịch bản mình vừa tạo — đây là phần
> nâng cao, hoàn toàn không bắt buộc và không ảnh hưởng tới điểm của các tiêu chí chính.

## Sản phẩm tối thiểu

- Agent chạy được trọn vẹn: nhập chủ đề, nhận về hồ sơ tài liệu và kịch bản.
- Hồ sơ tài liệu: mỗi nguồn ghi rõ lấy ở đâu, ai viết, đăng ngày nào, đáng tin tới đâu và vì sao.
- Kịch bản đúng mẫu, mỗi câu có thông tin đều dẫn được về nguồn.
- Màn hình duyệt nguồn: xem, bỏ, thêm nguồn và cho viết lại phần liên quan.
- Tự soát trích dẫn: đoạn trích phải khớp nội dung trang đã tải về, không phải do AI bịa.
- Xuất được kịch bản và hồ sơ tài liệu ra file.
- Đội tự chuẩn bị bộ trang web để thử các chỗ khó nêu dưới đây, và nộp kèm bài.
- Tài liệu hướng dẫn: cách chạy, chi phí mỗi lần chạy, và những gì hệ thống chưa làm được.

## Những chỗ sẽ khó

| Chỗ khó | Vì sao khó |
|---|---|
| Trang web cài sẵn lệnh ẩn để lừa AI làm theo | Chữ trên trang là **dữ liệu để đọc**, không phải lệnh để làm theo |
| Hai nguồn đều uy tín nhưng đưa số liệu khác nhau | Không được im lặng chọn một cái |
| Nguồn đã cũ hoặc đã có bản mới thay thế | Đúng lúc viết ≠ đúng lúc phát hành |
| Chủ đề gần như không có tài liệu tiếng Việt | Phải xoay sang nguồn ngoại ngữ và nói rõ |
| Đường dẫn hỏng, hoặc trang bắt đăng nhập mới đọc được | Không được coi như đã đọc |

## Không gian mở

- Tìm kiếm bằng dịch vụ có sẵn, bằng tính năng tra web của model, bằng công cụ tự thu thập trang, hoặc kết hợp.
- Một agent làm hết, hoặc chia nhiều agent: đi tìm, thẩm định, viết, soát trích dẫn.
- Chấm độ tin cậy bằng bộ tiêu chí cứng, bằng AI, hoặc cả hai.
- Làm với nguồn tiếng Việt, tiếng Anh hoặc nhiều thứ tiếng.
- Giao diện: web, ứng dụng máy tính, hoặc chạy bằng dòng lệnh — đội tự chọn.

## Demo bắt buộc

Ban giám khảo đưa một chủ đề tại chỗ, kèm mục tiêu bài học và thời lượng. Đội nhập vào và cho xem quá
trình hệ thống tìm rồi sàng lọc tài liệu. Mở hồ sơ tài liệu, bỏ một nguồn, chứng minh chỉ những câu liên
quan được viết lại. Ban giám khảo chỉ bất kỳ một câu trong kịch bản, hệ thống phải mở đúng đoạn tài liệu
chứng minh cho câu đó. Cuối cùng, đội cho chạy hai tình huống đã chuẩn bị sẵn — một trang có lệnh ẩn và
hai nguồn nói ngược nhau — để thấy hệ thống phản ứng thế nào.

## Chấm điểm

| Tiêu chí | Tỉ trọng |
|---|---|
| Câu truy được về nguồn và trích dẫn chính xác | 25% |
| Chọn nguồn đáng tin, còn mới | 20% |
| Kịch bản đọc lên nghe tự nhiên | 20% |
| Người duyệt kiểm soát được, chỉ viết lại phần cần sửa | 15% |
| Chịu được tình huống xấu | 10% |
| Dễ dùng, chạy lại cho kết quả tương đương | 10% |

### Điểm cộng

- Chỉ ra chỗ các nguồn mâu thuẫn và trình bày để người duyệt chọn.
- Theo dõi nguồn đã dùng, báo khi nguồn đó có bản cập nhật.
- Tìm được ví dụ thực tế ở Việt Nam, có dẫn nguồn.
- Gợi ý cách hiện tên nguồn ngay trên màn hình video.
- So sánh mù: giấu nhãn, để người đọc chấm kịch bản của máy và của người cùng một chủ đề.
- NÂNG CAO (không bắt buộc): dựng luôn một video hoàn chỉnh từ chính kịch bản agent vừa viết.

## An toàn và đạo đức

- Không bịa nguồn, không bịa trích dẫn.
- Chữ trên trang web là dữ liệu để đọc, không phải lệnh để làm theo.
- Tôn trọng bản quyền và điều khoản của trang được lấy nội dung.
- Nói rõ chỗ nào chưa chắc chắn, chỗ nào còn nhiều quan điểm khác nhau.
- Kịch bản do AI viết phải có giảng viên duyệt trước khi dựng thành video.

---

# Trong gói này có gì

| File | Là gì |
|---|---|
| [mau-kich-ban.md](mau-kich-ban.md) | **Mẫu kịch bản** — kịch bản agent sinh ra phải theo mẫu này |
| [vi-du/kich-ban-d1.md](vi-du/kich-ban-d1.md) · [vi-du/kich-ban-d1.json](vi-du/kich-ban-d1.json) | **Kịch bản của một video thật đã phát hành**, 40 câu — đích cần đạt |
| [vi-du/ho-so-nguon-mau.json](vi-du/ho-so-nguon-mau.json) | Một hồ sơ tài liệu đã điền — 5 nguồn, 6 thông tin, có cả nguồn bị loại và số liệu chưa xác minh |
| [vi-du/kich-ban-co-nguon.json](vi-du/kich-ban-co-nguon.json) | **Bảy câu kịch bản đã nối vào hồ sơ trên** — đây là thứ tiêu chí 25% chấm |
| [chu-de-goi-y.md](chu-de-goi-y.md) | Các chủ đề để luyện |

## Bắt đầu từ đâu

1. Đọc [vi-du/kich-ban-d1.md](vi-du/kich-ban-d1.md) trước tiên. Đó là đích: kịch bản của bạn phải trông
   như thế này.
2. Đọc [mau-kich-ban.md](mau-kich-ban.md) để biết luật viết — nhất là mục *Viết sao thì nghe vậy* và
   *Không bịa số liệu*.
3. Mở [vi-du/kich-ban-co-nguon.json](vi-du/kich-ban-co-nguon.json) cạnh
   [vi-du/ho-so-nguon-mau.json](vi-du/ho-so-nguon-mau.json). Lấy câu 9, lần theo mã `t01`, đọc hai đoạn
   trích chứng minh cho nó. Đó chính xác là thao tác ban giám khảo sẽ làm khi chấm.
4. Chọn một chủ đề trong [chu-de-goi-y.md](chu-de-goi-y.md), chạy thử tay một vòng: tự tìm ba nguồn, tự
   điền vào hồ sơ tài liệu, tự viết năm câu. Làm tay một lần rồi mới dựng agent thì đỡ đi nhầm đường.
5. Dựng agent.


---

## Ban tổ chức cấp gì, đội tự lo gì

Ban tổ chức chỉ cấp **khung** — định dạng phải theo, và vài ví dụ đã điền để nhìn cho dễ hiểu.
**Dữ liệu để chạy và để tự chấm là việc của đội.** Phần tự chuẩn bị dữ liệu cũng được tính điểm: bộ dữ
liệu nghèo nàn thì không chứng minh được hệ thống làm được gì.

### Đội tự lo

- **Khóa và tiền dùng model, dịch vụ tìm kiếm.** Có nhiều dịch vụ có mức miễn phí đủ cho một kỳ
  hackathon; hãy chọn theo hạn mức và ghi rõ trong tài liệu hướng dẫn đội đã dùng gì.
- **Bộ trang web để thử tình huống khó.** Muốn thử trang có lệnh ẩn hay hai nguồn mâu thuẫn thì tự dựng
  vài trang tĩnh rồi trỏ agent vào — vừa chủ động, vừa chạy lại được nhiều lần.
- **Bộ đánh giá của riêng đội.** Muốn chứng minh hệ thống tốt lên qua từng vòng thì phải tự có cách đo.
