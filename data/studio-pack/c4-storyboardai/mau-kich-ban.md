# Mẫu kịch bản chung

**Cả ba đề C3, C4, C5 dùng chung mẫu này.** C3 sinh ra kịch bản theo mẫu, C4 nhận phần lời đọc của
kịch bản theo mẫu, C5 trả về một kịch bản mới cũng theo mẫu. Nhờ vậy sản phẩm của ba đội ghép được
với nhau thành một dây chuyền.

Đây là mẫu cho **một clip bài giảng bình thường**: một người dẫn, không hội thoại, không câu hỏi tương tác.

---

## Đầu kịch bản

Vài dòng cho người dựng biết video này để làm gì. Không ai đọc phần này thành tiếng.

```markdown
# D4-00 · Tổng quan Ngày 04 — Nói sao cho AI hiểu đúng ý

- **Mục tiêu:** hết video người xem trả lời được hôm nay học gì, làm được gì, mang về gì.
- **Thời lượng dự kiến:** khoảng ba phút rưỡi.
- **Giọng đọc:** một người dẫn, giọng nữ miền Bắc.
```

---

## Thân kịch bản

Chia video thành các **phần**, mỗi phần là một tiêu đề `##`. Tên phần sẽ thành tên chương khi video lên
YouTube — đặt tên theo ý của phần, đừng đặt "Phần 1".

Trong mỗi phần, mỗi mục là **một câu được đọc = một cảnh**:

```markdown
## 1 · Mở đầu

### Câu 1
- **Kiểu:** kể
- **Lời:** Hai người hỏi trí tuệ nhân tạo cùng một việc, nhưng nhận về hai kết quả khác hẳn nhau.
- **Trên màn hình:** Hai kết quả, một câu hỏi
- **Ý đồ hình:** Hai khung kết quả đặt cạnh nhau, một sáng, một mờ.

### Câu 2
- **Kiểu:** chốt
- **Lời:** Khác nhau nằm ở cách hỏi.
- **Trên màn hình:** Khác nhau nằm ở CÁCH HỎI
- **Ý đồ hình:** Dòng chữ lớn giữa màn hình, các khung trước đó mờ đi.
```

### Bốn trường của một câu

| Trường | Bắt buộc | Là gì |
|---|---|---|
| **Lời** | có | Lời đọc **nguyên văn**. Máy đọc đúng từng chữ, phụ đề hiện đúng từng chữ. Đổi một chữ sau khi đã thu giọng là phải thu lại cả câu đó. |
| **Trên màn hình** | có | **Chữ** hiện lên trong cảnh. Không phải lời đọc, và **được phép khác lời đọc**: lời đọc nói "vai trò, nhiệm vụ, bối cảnh, định dạng" thì màn hình vẫn có thể để `VAI TRÒ · NHIỆM VỤ · BỐI CẢNH · ĐỊNH DẠNG`. Tối đa 40 ký tự. |
| **Ý đồ hình** | có | Mô tả **hình** cần thấy: cái gì xuất hiện, sắp xếp ra sao, chuyển động thế nào. Viết thứ cần *thấy*, đừng viết lại thứ đã *nghe*. |
| **Kiểu** | không | Cách đọc, một trong năm kiểu ở bảng dưới. Bỏ trống thì hiểu là *giảng*. |

Một câu có thể là **khoảng lặng** — dùng `- **Dừng:** 5 giây` thay cho `Lời` (ví dụ chừa thời gian cho
người xem suy nghĩ). Câu đó vẫn có hình.

---

## Một câu là một câu

Mỗi mục **Lời** nên là **một câu**. Một mục chứa ba câu thì cả ba dồn vào một cảnh, và cảnh đó phải gánh
ba ý cùng lúc.

Ngược lại, đừng tách những mẩu quá ngắn thành mục riêng ("Hết.", "Một.", "Vì sao?"). Chúng thành cảnh
chưa tới nửa giây — viết liền vào câu bên cạnh.

---

## Viết sao thì nghe vậy

Máy đọc đúng từng ký tự, nên lời đọc phải là thứ **phát âm được**:

- **Không có chữ số.** Viết "một trăm hai mươi từ", "hai ngày". Trên màn hình thì cứ để số bình thường.
- **Không viết tắt** mà người đọc không đọc thành tiếng: "CTA", "JSON", "v.v." — thay bằng lời đầy đủ,
  hoặc chỉ để trên màn hình.
- **Thuật ngữ tiếng Anh đi kèm nghĩa tiếng Việt, nghĩa đặt TRƯỚC**, ở lần nhắc đầu tiên trong video:

> "câu lệnh mình viết cho mô hình, gọi là prompt" · "đơn vị chữ mà mô hình đọc và tính tiền, gọi là token"

Vừa để người xem không rớt lại, vừa để nếu máy đọc thuật ngữ sai thì nghĩa vẫn đã được nói.

---

## Năm kiểu đọc

Kiểu đổi **tốc độ đọc** — đây là thứ tạo nhịp lên xuống. Chỉ có năm kiểu này, kiểu lạ ("mạnh", "vui")
không hợp lệ.

| Kiểu | Viết là | Tốc độ | Dùng cho |
|---|---|---|---|
| kể | `ke` | ×1,06 | kể chuyện, ví dụ — nhanh hơn, tươi hơn |
| giảng | `giang` | ×1,00 | giải thích khái niệm |
| thân mật | `nhe` | ×0,95 | nói riêng với một người |
| hỏi | `hoi` | ×0,90 | câu hỏi |
| chốt | `nhan` | ×0,86 | câu chốt — chậm lại, nặng tay |

Đừng để một đoạn dài cùng một kiểu, giọng sẽ đều đều. Đây là lỗi đã gặp thật ở một bộ video trước.

---

## Không bịa số liệu

Cảnh chỉ được cho thấy những con số, kết quả, tên riêng **có trong kịch bản**. Muốn màn hình có
"giảm 40%" thì **Lời** hoặc **Trên màn hình** phải nói ra con số đó. Người dựng sẽ không tự thêm.

---

## Mốc giờ thì đừng viết

Nếu kịch bản mang từ nơi khác sang có cột mốc giờ, **bỏ đi**. Quy trình làm loại video này là thu giọng
trước: máy đọc xong, đo thời lượng thật của từng câu, rồi cảnh mới dựng theo đúng thời lượng đó. Mốc viết
tay chỉ gây hiểu nhầm.

Muốn ước thời lượng thì tính khoảng **2,9 tiếng (âm tiết) mỗi giây**. Một câu 20 tiếng ≈ 7 giây.

---

## Nếu chương trình của bạn cần dạng JSON

Markdown là để người đọc. Máy đọc thì tiện hơn ở dạng này — cùng nội dung, chuyển qua lại được:

```json
{
  "id": "d1",
  "tieuDe": "Phân biệt trí tuệ nhân tạo, học máy, tạo sinh và mô hình ngôn ngữ lớn",
  "phan": [{ "so": 1, "ten": "Mở đầu — hai công cụ, hai nhiệm vụ" }],
  "cau": [
    {
      "n": 1,
      "phan": 1,
      "kieu": "ke",
      "loi": "Một công cụ đánh dấu thư nào có thể là thư rác, còn một trợ lý viết giúp bạn lời mời tham gia câu lạc bộ.",
      "chuTrenManHinh": "Hai ví dụ minh họa · Hai nhiệm vụ",
      "yDoHinh": "Hai thư điện tử chạy vào hai nhánh: một thư được gắn nhãn, nhánh kia xuất hiện bản nháp mới."
    },
    { "n": 35, "phan": 5, "dungGiay": 5, "chuTrenManHinh": "5 giây suy nghĩ" }
  ]
}
```

Tên trường tương ứng với các mục ở trên: `loi` ↔ **Lời**, `chuTrenManHinh` ↔ **Trên màn hình**,
`yDoHinh` ↔ **Ý đồ hình**, `kieu` ↔ **Kiểu**, `dungGiay` ↔ **Dừng**.

Có thêm một trường **chỉ C3 dùng**: `nguon` — danh sách mã những thông tin trong hồ sơ tài liệu đã
chứng minh cho câu này.

```json
{ "n": 9, "phan": 2, "loi": "Cách học từ dữ liệu ấy được gọi là học máy.", "nguon": ["t01"] }
```

Câu chỉ chuyển ý hoặc dẫn dắt thì không cần nguồn.

Chỉ có hai điều cần giữ, vì ba đề dùng chung định dạng này và sản phẩm của các đội phải ghép được với nhau:

- **`n` là số câu, không trùng, tăng dần.** Mọi thứ khác trỏ về câu bằng số này.
- **Mỗi câu có `loi` hoặc `dungGiay`**, không có cả hai.

Thêm trường riêng của đội thì cứ thêm. Ví dụ đầy đủ của một video thật nằm trong thư mục `vi-du/`.
