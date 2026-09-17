# C4 · StoryboardAI — Agent dựng kịch bản hình ảnh cho video bài giảng

**Tóm tắt: đưa vào lời đọc của một video, nhận về kế hoạch hình cho từng câu kèm ảnh phác.**

> Đề chính thức và cách cắt lát cho hackathon: `tracks/track-c-lesson-studio.md`. Thư mục này là tài liệu đi kèm.

---

## Bối cảnh

Video bài giảng dạng đồ họa chuyển động cần một bản kế hoạch hình cho từng câu: câu này người xem nhìn
thấy gì, sắp xếp ra sao, chữ nào hiện lên, hình chạy vào đúng lúc đọc tới từ nào. Hiện người viết kịch bản
phải tự nghĩ ra rồi mô tả bằng lời cho bốn, năm chục câu mỗi video — phần việc chiếm nhiều thời gian nhất
và cũng là chỗ đuối nhất. Người duyệt thì chỉ nhìn thấy hình khi cảnh đã dựng xong, mà dựng một video bằng
AI mất hàng chục phút và tốn tiền, nên cảnh trống, hình lạc đề hay hình không nhất quán chỉ lộ ra ở phút
cuối. Công cụ vẽ bằng AI hiện nay cho ra khung hình đẹp, nhưng mỗi khung một kiểu: một ký hiệu mang nghĩa
ở phút đầu, tới phút sau đã thành thứ khác.

## Bài toán

Hãy xây dựng một agent nhận vào phần lời đọc đã chốt của một video — chia sẵn theo câu, kèm mốc thời gian
của từng từ — rồi trả về bản kế hoạch hình cho cả video. Mỗi câu cần có đủ: người xem phải thấy ý gì, hình
thể hiện ra sao, chữ gì hiện trên màn hình, hình chạy vào lúc đọc tới cụm từ nào, và một **ảnh phác** để
người duyệt nhìn là hiểu ngay.

**Phong cách hình ảnh do đội tự nghĩ ra.** Không có thư viện hình hay bộ nhận diện nào bắt phải theo —
nhưng đội phải khai phong cách của mình thành một **sổ quy ước**: màu nào mang nghĩa gì, ký hiệu nào chỉ
cái gì, nhân vật nào xuất hiện thế nào. Hệ thống phải giữ đúng sổ quy ước của chính nó suốt cả video, và
tự báo khi nó phá quy ước. Người duyệt góp ý cho một câu thì chỉ câu đó đổi, các câu khác giữ nguyên.

Chỗ khó nhất của đề này là tách **"ý muốn truyền đạt"** khỏi **"cách vẽ ra"**: cùng một bản kế hoạch phải
chuyển sang một phong cách khác được mà không mất ý. Hình chỉ được thể hiện những gì lời đọc có, không tự
thêm con số, tên riêng hay kết quả mà kịch bản không nói. Ngoài các yêu cầu đó, đội thi tự chọn cách vẽ
phác, cách dựng agent và giao diện duyệt.

> **PHẠM VI:** đội thi chỉ cần làm ra kế hoạch hình, **không phải dựng thành video**. Đội nào giải xong
> bài toán chính mà còn thời gian thì có thể dựng luôn một video từ chính kế hoạch hình mình vừa tạo —
> đây là phần nâng cao, hoàn toàn không bắt buộc và không ảnh hưởng tới điểm của các tiêu chí chính.

## Sản phẩm tối thiểu

- Agent chạy được trọn vẹn: nhập lời đọc, nhận về kế hoạch hình cho cả video.
- Mỗi câu một cảnh, có **ảnh phác** nhìn là hiểu.
- **Sổ quy ước hình ảnh** do đội tự định nghĩa, và hệ thống giữ đúng nó suốt video.
- Bảng duyệt; góp ý một câu thì chỉ câu đó vẽ lại.
- **Tự soát**: báo khi một cảnh phá quy ước của chính đội.
- Chạy được trên ít nhất hai bộ lời đọc: file mẫu ban tổ chức cấp và một video do đội tự chuẩn bị.
- Tài liệu hướng dẫn: cách chạy, chi phí và những gì hệ thống chưa làm được.

Ba điều duy nhất về hình mà ban tổ chức quy định — khung 1920×1080 ở 30 hình/giây, vùng an toàn, và chữ
trên màn hình tối đa 40 ký tự — nằm ở [khung-hinh.md](khung-hinh.md). Ngoài ba điều đó, mọi thứ là của đội.

## Những chỗ sẽ khó

Năm chỗ này đều có sẵn trong file lời đọc mẫu, nên thử được ngay:

| Chỗ khó | Ở đâu trong bộ dữ liệu |
|---|---|
| Câu trừu tượng, không có vật gì cụ thể để vẽ | **câu 29** — "Cách chọn vẫn dựa vào phần câu đã có và quy tắc của hệ thống, chứ không ghép chữ tùy tiện." |
| Câu nhồi quá nhiều ý so với thời gian đọc | **câu 31** — bốn thứ phải kiểm tra, gói trong tám giây rưỡi |
| Một khái niệm nhắc lại sau vài phút, phải vẽ giống lần trước | **"mảnh văn bản / token"** xuất hiện ở câu 5 (00:24) rồi quay lại ở câu 40 (04:00) |
| Lời đọc ám chỉ có số liệu nhưng không nêu con số nào | **câu 13** — "bảng minh họa có các lựa chọn mưa, nắng, lạnh" mà không cho một phần trăm nào; câu 14 còn nói rõ các tỷ lệ là dựng ví dụ, không lấy từ mô hình thật |
| Đổi phong cách giữa chừng mà không mất ý | tự chọn một đoạn để thử |

## Không gian mở

- **Phong cách hình hoàn toàn tự chọn**: sơ đồ, minh hoạ, ảnh, chữ động, hay trộn nhiều kiểu.
- Vẽ phác bằng AI sinh ảnh, bằng hình vector do AI viết, bằng khung xám đơn giản, hay dựng bằng mã.
- Lên khung cả video trước rồi mới chi tiết từng câu, hoặc làm ngược lại.
- Góp ý bằng chữ, bằng giọng nói, bằng khoanh vùng trên ảnh, hoặc chọn giữa vài phương án được đề xuất.
- Giao diện: bảng duyệt trên web, ứng dụng máy tính, hoặc chạy bằng dòng lệnh — đội tự chọn.

## Demo bắt buộc

Nạp lời đọc của một video và dựng kế hoạch hình cho cả video, rồi mở bảng duyệt. Chạy hai lần: một lần
trên file mẫu ban tổ chức cấp, một lần trên video do đội tự chuẩn bị. Đội trình bày sổ quy ước hình ảnh của mình, rồi chỉ ra ít nhất hai quy ước được
giữ giống nhau từ đầu đến cuối video. Gõ một câu góp ý cho một cảnh và cho thấy chỉ cảnh đó đổi. Đổi phong
cách cho một đoạn và cho thấy ý vẫn nguyên. Ban giám khảo chọn một câu trừu tượng để xem hệ thống minh họa
thế nào khi không có vật gì cụ thể để vẽ.

## Chấm điểm

| Tiêu chí | Tỉ trọng |
|---|---|
| Hình phục vụ đúng ý dạy học | 25% |
| Nhất quán xuyên suốt video | 20% |
| Đổi phong cách mà giữ nguyên ý | 15% |
| Dựng được thành cảnh thật | 15% |
| Sửa từng phần và trải nghiệm duyệt | 15% |
| Chịu được tình huống xấu | 10% |

Lưu ý cách chấm **nhất quán**: ban giám khảo không so hình của bạn với một chuẩn nào bên ngoài, mà so với
**chính sổ quy ước bạn khai ra**. Đội khai hai quy ước rồi giữ đúng cả hai ăn điểm cao hơn đội khai mười
quy ước rồi phá năm.

### Điểm cộng

- Đề xuất vài phương án hình cho một câu để người duyệt chọn.
- Ghép ảnh phác với giọng đọc thành bản nháp chạy đúng thời lượng để xem thử.
- Phát hiện chỗ hình cần số liệu mà kịch bản chưa cung cấp.
- Không truyền đạt thông tin chỉ bằng màu, để người khó phân biệt màu vẫn hiểu.
- NÂNG CAO (không bắt buộc): dựng luôn một video hoàn chỉnh từ chính kế hoạch hình vừa tạo.

## An toàn và đạo đức

- Không thêm số liệu, tên riêng hay logo mà kịch bản không có.
- Không dùng logo, giao diện sản phẩm, nhân vật có bản quyền hay ảnh người thật khi chưa được phép.
- Tránh định kiến khi vẽ con người (giới tính, vùng miền, nghề nghiệp).
- Ví dụ tự nghĩ ra phải ghi rõ là hình minh họa.

---

# Trong gói này có gì

| File | Là gì |
|---|---|
| [vi-du/loi-doc-d1-2.json](vi-du/loi-doc-d1-2.json) | **Đầu vào chính** — lời đọc 42 câu của một video thật, kèm mốc thời gian từng từ, **đã bỏ hết mô tả hình** |
| [vi-du/loi-doc-d1-2.md](vi-du/loi-doc-d1-2.md) | Bản dễ đọc của file trên |
| [khung-hinh.md](khung-hinh.md) | Ba điều duy nhất được quy định về hình |
| [vi-du/storyboard-mau.json](vi-du/storyboard-mau.json) | Ba cảnh mẫu đã điền, để tham khảo — cấu trúc cụ thể do đội tự quyết |
| [mau-kich-ban.md](mau-kich-ban.md) | Mẫu kịch bản, để hiểu lời đọc từ đâu ra |

## Mốc thời gian từng từ

Mỗi câu trong `loi-doc-d1-2.json` có trường `mocTu`, là danh sách cặp `[viTriKyTu, frame]`:

```json
"loi":        "Khi một trợ lý hội thoại trả lời, các bạn thường thấy chữ xuất hiện dần trên màn hình.",
"chuoiMocTu": "Khi một trợ lý hội thoại trả lời, các bạn thường thấy chữ xuất hiện dần trên màn hình.",
"mocTu": [[0, 0], [4, 5], [8, 9], [12, 16], [15, 21], [19, 26], ...]
```

- `viTriKyTu` — chỉ số ký tự trong chuỗi `chuoiMocTu`. Số 4 trỏ vào chữ "một", số 8 trỏ vào "trợ".
- `frame` — frame bắt đầu đọc từ đó, **tính từ đầu câu này**, 30 frame = 1 giây. Chữ "hội" bắt đầu ở
  frame 21, tức 0,7 giây sau khi câu bắt đầu.

`chuoiMocTu` gần như luôn trùng `loi`. Chỉ khác ở bốn câu có thuật ngữ được ghi lại cách đọc cho máy —
ví dụ câu 5, `loi` viết "token" còn `chuoiMocTu` viết "tô-ken". Luôn đếm ký tự trên `chuoiMocTu`.

Đây là thứ cho phép hình chạy vào **đúng lúc người dẫn đọc tới từ đó**. Cho hình vào sớm hơn vài frame so
với lúc đọc tới từ đó thì xem dễ chịu hơn.

## Bắt đầu từ đâu

1. Mở [vi-du/loi-doc-d1-2.md](vi-du/loi-doc-d1-2.md), đọc hết 42 câu một lượt để nắm mạch video.
2. **Tự vẽ tay năm câu đầu.** Chưa cần code. Chính lúc này bạn sẽ quyết định phong cách của mình và phát
   hiện mình cần những quy ước gì.
3. Viết sổ quy ước ra giấy, rồi mới dựng agent.


---

## Ban tổ chức cấp gì, đội tự lo gì

Ban tổ chức chỉ cấp **khung** — định dạng phải theo, và vài ví dụ đã điền để nhìn cho dễ hiểu.
**Dữ liệu để chạy và để tự chấm là việc của đội.** Phần tự chuẩn bị dữ liệu cũng được tính điểm: bộ dữ
liệu nghèo nàn thì không chứng minh được hệ thống làm được gì.

### Đội tự lo

- **Khóa và tiền dùng model.** Có nhiều dịch vụ có mức miễn phí; hoặc bỏ hẳn sinh ảnh mà vẽ phác bằng
  hình vector hay khung xám — cách nào cũng được chấm như nhau.
- **Đáp án chuẩn.** Video mẫu này có một bản kế hoạch hình gốc do người làm, nhưng được giữ kín. Vả lại
  nó chỉ là *một* cách làm, không phải cách đúng duy nhất.
- **Video thứ hai để chạy thử.** File lời đọc mẫu chỉ là một ví dụ. Đội phải tự chuẩn bị thêm ít nhất
  một video của mình — lời đọc chia theo câu, có mốc thời gian càng tốt — và chạy hệ thống trên đó.
  Ban giám khảo cũng có thể đưa một bộ lời đọc khác vào lúc chấm.
