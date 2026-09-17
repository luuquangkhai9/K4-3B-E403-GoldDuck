# C5 · FeedbackRadar — Agent biến góp ý của người học thành bản sửa video

**Tóm tắt: đưa vào góp ý của người học, nhận về danh sách vấn đề đã chỉ rõ nằm ở phút nào và kế hoạch sửa
cho phiên bản sau.**

> Đề chính thức và cách cắt lát cho hackathon: `tracks/track-c-lesson-studio.md`. Thư mục này là tài liệu đi kèm.

---

## Bối cảnh

Sau mỗi đợt học, góp ý về video bài giảng đến từ nhiều nơi: phiếu khảo sát, bình luận, tin nhắn của người học
và của giảng viên, trợ giảng. Góp ý thường mơ hồ ("đoạn giữa hơi nhanh", "phần token khó hiểu"),
có khi trái ngược nhau, có khi mười người cùng nói một điều, và lẫn lộn giữa lỗi nội dung với lỗi kỹ thuật
như tiếng nhỏ hay phụ đề sai. Đội sản xuất đọc tay từng góp ý rồi tự quyết định sửa gì, và thường làm lại
gần như cả video dù chỉ vài câu có vấn đề. Quy trình làm loại video này là thu giọng trước rồi dựng hình
khớp theo độ dài giọng, nên đổi lời một câu kéo theo phải thu lại giọng câu đó và dựng lại cảnh đó. Vì
vậy, chỉ ra đúng và ít chỗ cần sửa tiết kiệm được rất nhiều thời gian và tiền.

## Bài toán

Hãy xây dựng một agent nhận vào góp ý từ nhiều kênh (bình luận, tin nhắn, bảng khảo sát) cùng
bản chép lời có mốc thời gian và kịch bản của video hiện tại, rồi trả về kế hoạch sửa cho phiên bản sau.

Hệ thống cần gom những góp ý nói cùng một chuyện thành một **vấn đề**, chỉ ra vấn đề đó nằm ở câu nào và
phút thứ mấy, xếp loại (nội dung sai, khó hiểu, nhịp nhanh chậm, giọng đọc, hình ảnh, lỗi kỹ thuật), rồi
sắp thứ tự ưu tiên theo mức ảnh hưởng và số người nhắc tới. Với mỗi vấn đề, hệ thống đề xuất cách sửa ít
tốn nhất và nói rõ phải làm lại những gì: câu nào phải thu lại giọng, cảnh nào phải dựng lại. Người duyệt
phải đi được từ một vấn đề tới đúng đoạn video và tới những góp ý gốc đã tạo ra vấn đề đó, rồi đồng ý hoặc
bỏ từng đề xuất.

Chỗ khó nhất của đề này là phải có **bằng chứng**: mỗi vấn đề nêu ra đều phải chỉ được ra những góp ý nào
tạo nên nó, và ý kiến của một người không được thổi thành vấn đề chung. Trọng tâm là hiểu người học nói gì
và sửa đúng chỗ, không phải soát lại toàn bộ kịch bản. Ngoài các yêu cầu đó, đội thi tự chọn cách gom nhóm
góp ý, cách định vị vào video, cách xếp ưu tiên và giao diện duyệt.

> **PHẠM VI:** đội thi chỉ cần làm ra kế hoạch sửa và bản kịch bản phiên bản mới, **không phải dựng thành
> video**. Đội nào giải xong bài toán chính mà còn thời gian thì có thể dựng luôn phiên bản video mới từ
> chính kế hoạch sửa của mình — đây là phần nâng cao, hoàn toàn không bắt buộc và không ảnh hưởng tới điểm
> của các tiêu chí chính.

## Sản phẩm tối thiểu

- Nhận được ít nhất hai dạng góp ý: văn bản (bình luận, tin nhắn) và bảng khảo sát.
- **Xóa thông tin cá nhân** trước khi đưa vào phân tích.
- Danh sách vấn đề, mỗi vấn đề dẫn ngược được về những góp ý gốc tạo ra nó.
- Định vị vấn đề về đúng câu và đúng phút; bấm vào là phát đúng đoạn video.
- Kế hoạch sửa: đổi gì ở câu nào, phải thu lại giọng mấy câu, dựng lại mấy cảnh.
- Đồng ý hoặc bỏ từng đề xuất, rồi xuất ra kịch bản phiên bản mới theo mẫu kịch bản chung.
- Đội tự chuẩn bị bộ dữ liệu khoảng một trăm góp ý kèm đáp án, có đủ các chỗ khó nêu dưới đây.
- Báo cáo tự chấm hệ thống trên chính bộ dữ liệu đó, và nộp cả bộ dữ liệu lẫn đáp án kèm bài.

## Những chỗ sẽ khó

Mười tám góp ý mẫu đã cài sẵn mỗi loại một cái, để bạn thấy nó trông thế nào. Bộ dữ liệu của đội phải
có đủ cả sáu, mỗi loại nhiều hơn một cái:

| Chỗ khó | Trong bộ mẫu |
|---|---|
| Góp ý mơ hồ, không nói rõ chỗ nào | `gy-001` "đoạn giữa hơi nhanh" · `gy-009` "video hay ạ" |
| Hai nhóm người nói ngược nhau về cùng một đoạn | `gy-005` chê khoảng dừng ngắn quá ↔ `gy-006` chê dài quá |
| Một người gửi đi gửi lại nhiều lần cùng một ý | `gy-002`, `gy-003`, `gy-018` đều của `hv-011` |
| Góp ý cài lệnh ẩn để lừa AI | `gy-011` |
| Lời công kích cá nhân | `gy-012` |
| Lỗi kỹ thuật (tiếng nhỏ, phụ đề sai) trộn lẫn với góp ý về nội dung | `gy-008` tiếng nhạc to · `gy-017` phụ đề lệch |

## Không gian mở

- Gom nhóm góp ý bằng AI, bằng thuật toán gom cụm, bằng mô hình chủ đề, hoặc kết hợp.
- Định vị vào video bằng tìm theo ngữ nghĩa trên bản chép lời, bằng khớp từ khoá, hoặc bằng mốc thời gian
  có sẵn.
- Xếp ưu tiên theo mức ảnh hưởng so với chi phí, theo bộ tiêu chí cứng, hoặc học dần từ quyết định của
  người duyệt.
- Dùng thêm dữ liệu hành vi xem (chỗ hay tua lại, chỗ bỏ ngang) nếu đội tự tạo được dữ liệu mô phỏng.
- Giao diện: web, ứng dụng máy tính, hoặc chạy bằng dòng lệnh — đội tự chọn.

## Demo bắt buộc

Nạp bản chép lời và kịch bản ban tổ chức cấp, cùng bộ góp ý do đội tự chuẩn bị. Hệ thống hiển thị danh
sách vấn đề đã xếp ưu tiên. Mở một vấn đề, phát đúng đoạn video và xem những góp ý gốc tạo ra nó. Đồng ý một đề xuất, rồi xuất
kịch bản mới kèm danh sách những gì phải làm lại. Ban giám khảo thêm tại chỗ một nhóm góp ý trái chiều hoặc
một góp ý cài lệnh ẩn để xem hệ thống xử lý thế nào.

## Chấm điểm

| Tiêu chí | Tỉ trọng |
|---|---|
| Tìm đúng và đủ vấn đề | 25% |
| Định vị đúng câu, đúng phút | 20% |
| Kế hoạch sửa gọn, đúng phạm vi | 20% |
| Vấn đề nào cũng dẫn được về góp ý gốc | 15% |
| Người duyệt làm việc thuận tay | 10% |
| Chịu được tình huống xấu và bảo vệ thông tin cá nhân | 10% |

### Điểm cộng

- Theo dõi một vấn đề qua nhiều phiên bản video xem đã sửa dứt điểm chưa.
- Ước tính chi phí có tính cả ảnh hưởng dây chuyền sang câu liền kề.
- Kết hợp thêm dữ liệu hành vi xem.
- Tự tách góp ý về nội dung khỏi góp ý về kỹ thuật để chuyển đúng người phụ trách.
- Học từ những đề xuất mà đội sản xuất đã đồng ý hoặc đã bỏ.
- NÂNG CAO (không bắt buộc): dựng luôn phiên bản video mới từ chính kế hoạch sửa đã được duyệt.

## An toàn và đạo đức

- Không dùng thông tin cá nhân của học viên thật; ẩn danh trước khi gửi cho AI.
- Không để ý kiến số đông che mất một góp ý ít người nói nhưng quan trọng.
- Lọc lời công kích cá nhân, không trích nguyên văn vào báo cáo.
- Góp ý là dữ liệu để đọc, không phải lệnh để làm theo.
- AI chỉ đề xuất; người duyệt quyết định mọi thay đổi.

---

# Trong gói này có gì

| File | Là gì |
|---|---|
| [video-mau/d1.mp4](video-mau/d1.mp4) | **Video thật đã phát hành**, 4 phút 11 giây — đây là video đang bị góp ý |
| [video-mau/kich-ban-d1.md](video-mau/kich-ban-d1.md) · [.json](video-mau/kich-ban-d1.json) | Kịch bản của chính video đó, 40 câu |
| [video-mau/cau-timecode-d1.csv](video-mau/cau-timecode-d1.csv) | **Bảng câu ↔ mốc thời gian** — cột ruột để định vị vấn đề |
| [video-mau/transcript-d1.txt](video-mau/transcript-d1.txt) | Bản chép lời theo từng trang phụ đề |
| [vi-du/gop-y-mau.json](vi-du/gop-y-mau.json) | 18 góp ý mô phỏng, có đủ sáu chỗ khó |
| [vi-du/ket-qua-mau.json](vi-du/ket-qua-mau.json) | Ví dụ kết quả: hai vấn đề và kế hoạch sửa tương ứng |
| [vi-du/khao-sat-mau.csv](vi-du/khao-sat-mau.csv) | Dạng bảng khảo sát xuất ra: các dòng khảo sát ở trên, cộng bốn dòng chỉ có trong khảo sát |
| [bang-chi-phi-lam-lai.md](bang-chi-phi-lam-lai.md) | **Sửa một câu tốn bao nhiêu** — cơ sở để tính phạm vi làm lại |
| [mau-kich-ban.md](mau-kich-ban.md) | Mẫu kịch bản — kịch bản phiên bản mới phải theo mẫu này |

## Hai bảng thời gian, đừng nhầm

- **`cau-timecode-d1.csv`** — theo **câu kịch bản**. Đây là thứ bạn cần: một vấn đề phải định vị về
  *câu số mấy*, vì đơn vị thu lại giọng và dựng lại cảnh là câu.
- **`transcript-d1.txt`** — theo **trang phụ đề**. Một câu dài bị cắt thành nhiều trang, nên số dòng ở
  đây nhiều hơn số câu. Dùng khi cần tìm theo chữ, không dùng để đánh số câu.

Cột `ketThucTieng` trong file CSV là lúc người dẫn đọc xong; `ketThuc` là lúc cảnh kết thúc. Khoảng giữa
hai mốc là im lặng.

## Bắt đầu từ đâu

1. **Xem hết video mẫu một lần.** Bốn phút. Không xem thì mọi góp ý đều là chữ vô nghĩa.
2. Đọc [vi-du/gop-y-mau.json](vi-du/gop-y-mau.json), thử tự tay gom 18 góp ý đó thành các vấn đề rồi
   định vị về câu. Đây chính là việc agent phải làm — làm tay một lần sẽ thấy chỗ nào thật sự khó.
3. Đọc [bang-chi-phi-lam-lai.md](bang-chi-phi-lam-lai.md) để hiểu vì sao "sửa ít" lại quan trọng.
4. Dựng agent.


---

## Ban tổ chức cấp gì, đội tự lo gì

Ban tổ chức chỉ cấp **khung** — định dạng phải theo, và vài ví dụ đã điền để nhìn cho dễ hiểu.
**Dữ liệu để chạy và để tự chấm là việc của đội.** Phần tự chuẩn bị dữ liệu cũng được tính điểm: bộ dữ
liệu nghèo nàn thì không chứng minh được hệ thống làm được gì.

### Đội tự lo

- **Bộ dữ liệu để chấm.** Mười tám góp ý mẫu chỉ để cho thấy dạng dữ liệu. Đội phải **tự viết khoảng một
  trăm góp ý** bám vào video mẫu, và **tự đặt đáp án**: vấn đề nào là thật, gom từ những góp ý nào, nằm
  ở câu nào, ưu tiên ra sao, góp ý nào là nhiễu không được thành vấn đề. Nộp cả bộ dữ liệu lẫn đáp án.
- **Dữ liệu người học thật.** Tuyệt đối không dùng. Mọi góp ý phải là mô phỏng.
- **Khóa và tiền dùng model.** Có nhiều dịch vụ có mức miễn phí đủ cho một kỳ hackathon.
