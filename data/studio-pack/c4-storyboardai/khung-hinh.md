# Khung hình

Đây là **toàn bộ** những gì ban tổ chức quy định về hình:

- Khung 1920×1080, 30 hình mỗi giây.
- Nội dung dạy học nằm trong vùng an toàn; dải dưới cùng để trống cho phụ đề.
- Chữ trên màn hình tối đa 40 ký tự.

Ngoài ba điều này, mọi thứ về hình là của đội — không có thư viện hình, không có bảng màu, không có bộ
nhận diện nào bắt phải theo. Phần dưới chỉ giải thích ba điều trên cho rõ.

## 1. Kích thước và tốc độ

**1920 × 1080 điểm ảnh, 30 hình mỗi giây.**

Mọi mốc thời gian trong kế hoạch hình tính bằng *frame*: 30 frame = 1 giây, 15 frame = nửa giây.
File lời đọc cũng dùng đơn vị này.

## 2. Vùng an toàn

```
0 ────────────────────────────────────────────── 1920
│  vùng trên — nhãn, tiêu đề
│  ┌──────────────────────────────────────┐  y = 250
│  │                                      │
│  │      NỘI DUNG DẠY HỌC                │
│  │      x từ 80 đến 1840                │
│  │                                      │
│  └──────────────────────────────────────┘  y = 960
│  vùng phụ đề — để trống
└────────────────────────────────────────────── y = 1080
```

Phần người xem cần nhìn để hiểu bài phải nằm trong **y 250 → 960**, **x 80 → 1840**.

**Đừng đặt gì quan trọng dưới y = 984.** Dải cuối màn hình là chỗ phụ đề chạy, sẽ che mất.

## 3. Chữ trên màn hình: tối đa 40 ký tự

Đây là dòng chữ tóm ý của cảnh. Dài hơn thì không đọc kịp trong lúc người dẫn đang nói.

Phụ đề thì không phải việc của bạn — khâu dựng video tự thêm vào dải cuối màn hình.

---

## Gợi ý, không bắt buộc

Vài con số rút từ kinh nghiệm dựng những video trước, dùng được thì dùng:

| | |
|---|---|
| Một vật hiện ra | khoảng 24 frame (0,8 giây) |
| Nhấn mạnh một lần | khoảng 54 frame (1,8 giây) |
| Giữ trạng thái cuối cảnh | ít nhất 60 frame (2 giây) |

Cho hình chạy vào **sớm hơn vài frame** so với lúc người dẫn đọc tới từ đó thì xem dễ chịu hơn — mốc
thời gian từng từ nằm trong file lời đọc.

Và một điều đáng giữ dù không ai chấm: **hình chỉ nói điều lời đọc có**. Kịch bản không nêu con số thì
đừng vẽ con số. Cần số liệu mới rõ ý thì báo lên, đừng tự bịa.
