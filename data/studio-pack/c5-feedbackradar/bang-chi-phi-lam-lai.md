# Sửa một câu tốn bao nhiêu

Đề này chấm "kế hoạch sửa gọn, đúng phạm vi" 20%. Muốn biết một kế hoạch có gọn hay không thì phải quy
được ra chi phí. Dưới đây là mô hình chi phí **dùng chung cho cả cuộc thi** — mọi đội tính bằng cùng một
thước thì mới so được với nhau.

---

## Vì sao đổi một chữ lại tốn kém

Quy trình làm loại video này đi theo thứ tự: **kịch bản → thu giọng → dựng hình theo đúng độ dài giọng**.

Hình được dựng khớp từng frame với giọng đã thu. Nên đổi một chữ trong lời đọc kéo theo:

1. Thu lại giọng của câu đó → độ dài câu thay đổi.
2. Dựng lại cảnh của câu đó theo độ dài mới.
3. Xuất lại video.

Đổi **ý đồ hình** mà không đổi lời thì rẻ hơn nhiều: giọng giữ nguyên, chỉ dựng lại cảnh.

## Hai mức chi phí

| Loại thay đổi | Phải thu lại giọng | Phải dựng lại cảnh |
|---|---|---|
| Đổi lời (`loi`) | có | có |
| Đổi chữ trên màn hình | không | có |
| Đổi ý đồ hình | không | có |
| Đổi kiểu đọc (`kieu`) | có | có — độ dài đổi theo tốc độ |
| Bỏ hẳn một câu | không | có, và các câu sau bị dịch mốc |
| Thêm một câu mới | có | có, và các câu sau bị dịch mốc |

## Ảnh hưởng dây chuyền sang câu liền kề

Đây là điểm dễ bị bỏ sót nhất, và là chỗ ăn điểm của tiêu chí "kế hoạch sửa gọn".

Khi máy đọc một câu, nó được cho biết **câu ngay trước và câu ngay sau** để lấy ngữ điệu cho tự nhiên.
Hệ quả: đổi lời câu **N** thì ngữ cảnh của câu **N−1** và **N+1** cũng đổi, nên **cả ba câu đều phải thu
lại**, dù bạn chỉ sửa một câu.

```
Sửa câu 20  →  thu lại câu 19, 20, 21
Sửa câu 20 và 21  →  thu lại câu 19, 20, 21, 22   (không phải 6 câu)
```

Vì vậy **sửa hai câu liền nhau rẻ hơn sửa hai câu cách xa nhau**. Kế hoạch sửa tốt nên gom các thay đổi
lại gần nhau khi có thể.

## Đơn vị tính

Giọng tính tiền theo **số ký tự** của lời đọc.

Số liệu thật của video mẫu trong gói này:

| | |
|---|---|
| Số câu có lời đọc | 39 |
| Tổng ký tự | 3 637 |
| Trung bình mỗi câu | **93 ký tự** |
| Câu ngắn nhất / dài nhất | 43 / 118 ký tự |

## Báo chi phí thế nào

Không có công thức bắt buộc. Đội tự chọn cách quy đổi, miễn là **nhất quán** và **nói rõ đã quy đổi ra
sao**. Cách đơn giản nhất là đếm hai con số:

- bao nhiêu **ký tự** phải thu lại giọng (nhớ cộng cả hai câu liền kề);
- bao nhiêu **cảnh** phải dựng lại.

Rồi đặt cạnh con số của việc làm lại toàn bộ — 3 637 ký tự và 40 cảnh — để thấy tiết kiệm được bao nhiêu.
Xem [vi-du/ket-qua-mau.json](vi-du/ket-qua-mau.json) để có một ví dụ đã tính sẵn.

Điều đáng làm là **đừng quên ảnh hưởng dây chuyền**. Hệ thống nào chỉ đếm "sửa 2 câu" mà bỏ qua 2 câu liền
kề sẽ báo thiếu gần một nửa chi phí thật.
