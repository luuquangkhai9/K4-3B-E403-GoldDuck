# People + AI Guidebook (Google PAIR) — bản tóm lược cho hackathon

Nguồn: **People + AI Guidebook**, Google PAIR — https://pair.withgoogle.com/guidebook/ (nội dung gốc theo giấy phép CC BY-NC-SA 4.0). Đây là tóm lược tiếng Việt do BTC viết lại theo từng chương, kèm chỉ dẫn *dùng ở mục nào của `02-guide.md`* và *ghi vào đâu trong `spec.md`*. Đọc bản gốc khi cần chi tiết: mỗi chương trên web có Guiding Questions, Worksheet và ví dụ (Plannerific, Develocity, RUN).

| Chương PAIR | Dùng cho mục | Ghi vào spec |
|---|---|---|
| 1. User needs & defining success | §1.1, §1.4, §2.3 | §1–§2 pain/bằng chứng, §4 automation, §7 quality bar |
| 2. Data & model evolution | §1.3, §2.6, §4.1 | §7 golden set, định nghĩa "tốt" |
| 3. Mental models & expectations | §2.4, §3.2 | §4b nguyên tắc, onboarding của prototype |
| 4. Trust & explanations | §2.4, §2.5 | §4b, §5 chỗ khó ① nguồn sự thật |
| 5. Feedback & controls | §2.4, §4.2 | §4b, §9 changelog |
| 6. Errors & graceful failures | §2.5 | §5–§6 bốn lớp chỗ khó, kịch bản rủi ro |

---

## 1 · User needs & defining success — Nhu cầu người dùng và định nghĩa thành công

### 1.1 Xác định nhu cầu người dùng và thế mạnh của AI
- Hai lối vào: **people-first** (bắt đầu từ vấn đề thật của người dùng, kiểm chứng giả định) và **technology-first** (bắt đầu từ năng lực công nghệ). Cả hai đều được, nhưng luôn phải trả lời: *thêm AI vào có làm trải nghiệm tốt lên hay tệ đi?* Việc người dùng thích tự làm thì đừng tự động hoá.
- Hiểu **bản chất vấn đề**: phổ biến đến đâu, ảnh hưởng ai, tần suất, hoàn cảnh, mức nghiêm trọng, thay đổi theo thời gian không. Phỏng vấn cả người dùng "cực đoan" (dùng nhiều nhất / gặp khó nhất).
- Hiểu **cách người dùng đóng khung vấn đề** (specification alignment): mục tiêu chính · mục tiêu phụ · phần người dùng *không nói ra* (underspecification) · tối ưu một mục tiêu có làm hỏng mục tiêu khác không (reward hacking).
- Ba loại hệ thống và khi nào hợp: **AI dự đoán/phân loại** (tự động hoá, nhận diện, gợi ý, dự báo) · **AI sinh** (giảm tải nhận thức, tóm tắt, trả lời theo ngữ cảnh, sáng tạo) · **luật/heuristic** (cần dự đoán được, lỗi rất đắt, cần giải thích ổn định). Cân nhắc stakes, kỳ vọng xã hội, chi phí vận hành.
- Vẽ **workflow hiện tại** trước khi thiết kế; chỗ nào tự động hoá, chỗ nào tăng cường. Chưa có sản phẩm thì thử "Wizard of Oz".

*Dùng cho hackathon:* §1.1 năm câu hỏi và §1.4 bảng impact. Câu "AI có hợp không" chính là tiêu chí 3 (problem statement không có chữ AI).

### 1.2 Cân bằng tự động hoá (automation) và tăng cường (augmentation)
- Hỏi trước: người dùng đang cố làm gì, hiểu AI đến đâu, nếu có trợ lý người thì họ giao việc gì?
- **Tự động hoá hợp khi:** việc vượt kỹ năng người dùng · việc gấp/thủ công máy làm tốt hơn · việc lặp, giá trị thấp, chán · quy trình dự đoán được, ít rủi ro. Đo bằng: hiệu năng, hiệu quả, hài lòng, an toàn.
- **Tăng cường hợp khi:** người dùng *thích* làm việc đó (sáng tạo) · người dùng *chịu trách nhiệm* hậu quả (quyết định y tế, pháp lý) · rủi ro vật lý/cảm xúc/xã hội/văn hoá · nhu cầu phức tạp, mơ hồ, đối thoại · việc nhiều bước kéo dài. Đo bằng: cảm giác làm chủ, kiểm soát được tự động hoá, mở rộng năng lực.
- Cảnh giác **automation complacency / bias**: hậu quả càng lớn, càng cần người giám sát.

*Dùng cho hackathon:* §2.3 chọn mức Augment / Conditional / Automate — viết lý do theo cost-of-error, không viết "vì tiện".

### 1.3 Định nghĩa chính sách thiết kế tương tác (interaction design policies)
Với AI sinh, người dùng có thể yêu cầu bất cứ thứ gì → cần "luật" cho từng **khoảnh khắc then chốt** (critical moment) trong hành trình:
- **Hành động chấp nhận** — "Chúng tôi muốn {người dùng} dùng AI để {việc}"; "AI luôn phải {tiêu chí đầu ra}". Kèm ràng buộc input, ràng buộc output, metric.
- **Hành động không chấp nhận** — "AI không được tạo ra {…}" kể cả khi người dùng vô tình yêu cầu; chỗ nào cần người giám sát; test đối kháng.
- **Ngưỡng bất định** — kết quả đúng một phần thì khi nào được hiện? "Nếu AI dự đoán yếu, người dùng không phiền {việc sửa nhỏ} miễn là {điều kiện}". Kèm khung cảnh báo: *Nếu {metric} {giảm dưới/vượt} {ngưỡng} thì chúng tôi {hành động}*.
- **Điểm dễ tổn thương** — lỗi nào không phục hồi được; thay đổi ngữ cảnh nào biến kết quả hợp lý thành nguy hiểm.
- Quyết định precision hay recall theo hậu quả của false positive / false negative với người dùng; định nghĩa metric định lượng + tiêu chí định tính.

*Dùng cho hackathon:* đây chính là spec §4 (phạm vi/non-goals), §5–§6 (chỗ khó, kịch bản) và §7 (quality bar bằng số). Ba câu mẫu ở trên có thể chép thẳng vào spec.

### 1.4 Chuẩn bị cho các cạm bẫy
- Lập nhóm đa góc nhìn, hỏi: nếu chính sách không bao giờ bị vi phạm thì người dùng/xã hội ra sao? hiệu ứng bậc hai? 3 năm nữa còn đúng không?
- Nối hậu quả xấu với **thay đổi hành vi đo được** trong sản phẩm ("nếu tỉ lệ từ chối gợi ý > 20% thì kiểm tra model").
- Ví dụ giáo dục trong sách: AI hỗ trợ viết luận cho học sinh → bài giống nhau, giáo viên khó đánh giá → giải pháp: gắn nhãn "do AI viết / do học sinh viết", rồi cá nhân hoá đánh giá theo tiến bộ qua nhiều bản nháp.
- Bảng tác hại xã hội-kỹ thuật (Shelby et al., 2023): tác hại đại diện, phân bổ, chất lượng dịch vụ, liên cá nhân, xã hội.

---

## 2 · Data & model evolution — Dữ liệu và tiến hoá của model

### 2.1 Yêu cầu AI và dữ liệu
- Dữ liệu là "máu" của AI: model chỉ tốt bằng dữ liệu. Câu hỏi chất lượng: phản ánh thực tế không? thu thập/lưu có trách nhiệm không? bảo trì được không? có metadata? bản quyền/riêng tư đã xử lý?
- Dịch nhu cầu người dùng thành examples · features · labels; cân nhắc PII và đặc điểm được bảo vệ; cần bao nhiêu dữ liệu gán nhãn; đại diện cho người dùng thật không.
- **Tạo dữ liệu mẫu (prototypical data)** sớm: đoán input ngoài đời trông thế nào, đặt chuẩn "dữ liệu tốt", đánh giá tính đại diện, xây bộ eval phản ánh use case thật, lên kế hoạch test đối kháng (prompt injection, trích xuất dữ liệu, đầu độc).
- Các nguồn lỗi thường gặp: thiếu đại diện, lệch ngữ cảnh (lab vs. thực địa), không nhất quán khi gán nhãn, thiếu chuyên gia domain, không có vòng phản hồi từ triển khai, người dùng diễn đạt khác lúc train, phạm vi trôi dần.
- Tài liệu hoá bằng **Data Cards / Datasheets**.

### 2.2 Chuẩn bị dữ liệu
- Ba nguồn: dùng dữ liệu có sẵn · tự thu thập và gán nhãn · **dữ liệu tổng hợp** (synthetic) — có người kiểm định, so phân bố với dữ liệu thật nhỏ.
- Gán nhãn: nhận ra tính chủ quan, chuyên môn và trải nghiệm sống của người gán nhãn; hướng dẫn rõ, cho phép "không chắc"/bỏ qua; lưu bất đồng giữa người gán nhãn như một tín hiệu.
- Chia tập train / validation / test; bảo trì phòng ngừa – thích ứng – sửa lỗi; xin phép rõ khi dùng dữ liệu người dùng.

### 2.3 Tiến hoá AI bằng đánh giá (evaluation)
- **Bảy chiều chất lượng cho AI sinh:** Coverage (trả lời đủ mọi phần yêu cầu) · Relevance (đúng yêu cầu — như precision) · Diversity (đa dạng — như recall) · Sensitivity (đổi input nhỏ, output đổi hợp lý) · Realism (giống người làm) · **Factuality** (có căn cứ, không bịa) · Quality (mạch lạc, không lỗi hình thức).
- Làm ngược từ: vấn đề nào của người dùng? biết họ thành công bằng gì? "đủ tốt" là gì?
- Kết hợp metric model (BLEU/ROUGE…, calibration, robustness, consistency) với **metric trải nghiệm** (task success rate, time to completion, perceived accuracy, trust score) và **an toàn/công bằng** (toxicity, jailbreak resistance, demographic parity, hallucination/semantic entropy).
- Khi kết quả kém, hỏi theo tầng: lỗi do dữ liệu (thiếu domain, thiếu đại diện, drift)? do đầu ra (không nhất quán)? do chính sách thiết kế (precision/recall lệch, kịch bản mở)? hay do **giải thích kém** — không có lỗi nhưng người dùng tưởng là lỗi?

*Dùng cho hackathon:* §2.6 và §4.1 — chọn 2–3 chiều trong bảy chiều làm định nghĩa "tốt", mỗi chiều có cách chấm kiểm chứng được; §7 spec.

---

## 3 · Mental models & expectations — Mô hình tâm trí và kỳ vọng

### 3.1 Nhận diện mô hình tâm trí sẵn có
- Hỏi người dùng: họ nghĩ sản phẩm hoạt động ra sao? dùng ẩn dụ gì? đã dùng công cụ tương tự nào? chuyên gia và người mới dùng khác nhau thế nào? thương hiệu tạo kỳ vọng gì?
- Khi AI đổi cách làm việc, mô hình tâm trí cũ phải cập nhật — đó là dấu hiệu cần giải thích.

### 3.2 Đưa AI vào theo giai đoạn
- Khung câu giới thiệu: *"Đây là {tính năng}, nó giúp bạn {lợi ích}. Hiện nó chưa làm được {giới hạn}. Theo thời gian nó sẽ {thay đổi}. Bạn giúp nó tốt hơn bằng cách {hành động}."*
- Onboarding: nói **lợi ích** trước cách hoạt động; nêu vai trò/phạm vi AI, cách kiểm soát, cài đặt dữ liệu; nói trước AI sẽ sai ở đâu. Ba trường hợp *phải* giải thích công nghệ: sản phẩm cho doanh nghiệp/dev, tình huống rủi ro cao, người dùng không chuyên.
- **Inboarding:** giới thiệu tính năng AI *đúng lúc* người dùng cần (trigger event), thông điệp ngắn, hành động được ngay.
- Thiết kế cho **thử nghiệm an toàn**: người dùng được thử mà không ảnh hưởng dữ liệu thật; nhắc lại kỳ vọng thường xuyên; cho biết khi nào việc ngoài phạm vi.

### 3.3 Lên kế hoạch cùng học (co-learning)
- Nói rõ phản hồi của người dùng được dùng thế nào: ngay lập tức · lọc kết quả sau · fine-tune dài hạn · không dùng.
- Ba kiểu lệch thường gặp trong hội thoại: người dùng đổi chủ đề mà AI không nhận ra · người dùng mở rộng chủ đề mà AI tưởng đổi · người dùng hỏi thứ ngoài phạm vi (AI vẫn trả lời dù không được thiết kế cho việc đó).
- Biến lỗi thành cơ hội: thừa nhận giới hạn ngay lúc đó, đưa đường đi khác trong phạm vi, cho trích dẫn để tự kiểm, xin phản hồi.

### 3.4 Kỳ vọng "giống người"
- Nhân hoá AI có giá: người dùng so với năng lực người thật, mất tin khi giới hạn không rõ, **tiết lộ nhiều thông tin hơn**, ỷ lại thay vì hỏi chuyên gia.
- Năm mẫu hỗ trợ nhập liệu: mẫu input · hỏi làm rõ khi thiếu · báo trở ngại khi ngoài phạm vi · gợi ý bước tiếp · tóm tắt lại yêu cầu phức tạp.
- Không phải AI nào cũng cần giống người; nếu có, chủ động nhắc "đây là máy".

*Dùng cho hackathon:* §2.4 nguyên tắc G1/G2 và §3.2 prototype — câu chào/giới thiệu của tutor hay bot chính là onboarding; kiểm xem nó đặt kỳ vọng đúng chưa.

---

## 4 · Trust & explanations — Niềm tin và giải thích

### 4.1 Hiểu "niềm tin"
- Người ta tin qua: kết quả thành công khi dựa vào · cảm giác kết nối · trải nghiệm lặp lại theo thời gian.
- **Các đòn bẩy của niềm tin:** Authenticity (thừa nhận giới hạn/lỗi) · Benevolence · Competence · Consistency · Explainability · Expressiveness · Factuality · Integrity · Reliability · Transparency.
- **Niềm tin đúng mức** = kỳ vọng khớp năng lực thật. Over-trust: tin khi không nên (operator complacency; người mới tin quá vì autocomplete chỗ khác tốt). Under-trust: không tin dù đúng.
- Metric niềm tin cần nhạy, có ý nghĩa, khái quát được.

### 4.2 Hiệu chuẩn niềm tin xuyên suốt trải nghiệm
- Từ đầu: nói rõ dữ liệu nào ảnh hưởng kết quả; đặt mặc định có ý nghĩa; nói khi nào bắt đầu có lợi ích đầy đủ; **chuẩn bị người dùng cho lỗi thường gặp** (ví dụ: modal "chatbot có thể trả lời sai").
- Chiến lược: quản lý kỳ vọng · dựa trên quen thuộc · cho cấu hình · **hỗ trợ kiểm chứng và đối chiếu** (nhiều kết quả, nguồn gốc, phản chứng) · cơ chế lái/kiểm soát.
- Đánh giá tác động của lỗi lên niềm tin theo: mức nghiêm trọng · khả năng xảy ra · nguồn (hệ thống hay ngữ cảnh) · **khả năng nhận ra** (người dùng có biết là sai không?) · hậu quả thực. Bốn tình huống: lỗi thấy được · lỗi không thấy được · không lỗi nhưng sai ngữ cảnh · không lỗi nhưng người dùng tưởng lỗi.

### 4.3 Viết giải thích hữu ích
- Có cần giải thích không? Xét **stakes × complexity × cost**: tình huống quan trọng cỡ nào, người dùng tự kiểm chứng được không, hành động AI gợi ý tốn/khó hoàn tác không.
- Ba lớp giải thích: **in-product** (onboarding, giới thiệu tính năng) · **in-the-moment** (ngay tại kết quả, giúp quyết định tin/không tin, khuyến khích kiểm chứng) · **beyond-the-product** (help center, FAQ).
- Kiểu giải thích: nguồn dữ liệu nào chi phối · input nào của người dùng ảnh hưởng · so sánh phương án · phản chứng "đổi X thì ra Y" · ví dụ đa dạng · điểm/tiêu chí so sánh · giải thích một phần (partial) về nguồn và giới hạn.

*Dùng cho hackathon:* §2.4 G11 và chỗ khó ① nguồn sự thật — trích dẫn `[trang N]` là giải thích in-the-moment; tutor "chào bằng tên" và đoạn mở đầu dài là chỗ cần xem lại kỳ vọng.

---

## 5 · Feedback & controls — Phản hồi và kiểm soát

### 5.1 Nối phản hồi người dùng với cải tiến model
- Ba mức phản hồi: **toàn hệ thống** (rating, review) · **một phần** (một tính năng, kèm log) · **từng output** (đánh giá kết quả cụ thể).
- Đặt mục tiêu: *"Chúng tôi thu {loại phản hồi} để cải thiện {tương tác} bằng cách {thay đổi AI}."*
- **Tín hiệu hành vi hai nghĩa** — phải đọc theo ngữ cảnh: *Regenerate* (khám phá hay bất mãn?) · *Edit* (đồng sáng tạo hay AI sai nặng?) · *Dwell time* (chăm chú hay bối rối?) · *Copy/Share* (giá trị hay báo lỗi?) · *Bỏ qua* (gần như luôn tiêu cực) · *Follow-up* (đào sâu hay phải hỏi lại vì bị hiểu sai?).
- Động cơ cho phản hồi: tự thể hiện, vị tha, uy tín, lợi ích tức thì, phần thưởng, bức xúc cần giải quyết, biết ơn, áp lực. Mỗi loại có mặt trái.
- Đặt kỳ vọng sau khi nhận phản hồi: nói rõ **khi nào** và **phạm vi nào** thay đổi ("đã cập nhật" ≠ "sẽ cân nhắc").

### 5.2 Thiết kế vòng phản hồi
- Phản hồi **ngầm** (từ hành vi tự nhiên) và **tường minh** (yêu cầu người dùng làm thêm); kết hợp cả hai.
- Kiểu thu: thumbs up/down · một nút · thang điểm · so sánh nhiều kết quả · hành động gợi ý · câu hỏi tiếp theo (của người hoặc của AI) · ô văn bản · quan sát người dùng chỉnh input/sửa output.
- **Phản hồi từ hệ thống** cho người dùng: tiến độ theo bước, giải thích ngữ cảnh, chỉ báo chất lượng (confidence, nguồn), thông báo lỗi có lý do, gợi ý input.

### 5.3 Trao quyền kiểm soát
- Tương tác do người dùng khởi phát thường tốt hơn AI chủ động; luôn có bật/tắt, gợi ý không xâm phạm (ghost text), nhiều cách gọi (panel sâu / lệnh nhanh), mặc định không AI.
- Cấu hình: phạm vi (toàn cục hay theo tác vụ) · cách chọn (tag, thanh trượt, ví dụ, ngôn ngữ tự nhiên) · **bằng chứng tác dụng** (chọn "ngắn gọn" thì phải ngắn thật) · bộ nhớ ngắn/trung/dài hạn có thể xem, sửa, xoá.
- Lái và quản lý kết quả: sửa cục bộ thay vì tạo lại · xem lại các lần thử · chia nhỏ tác vụ · tạm dừng/huỷ không mất gì · xác nhận trước bước quan trọng · thu hồi quyền.
- Nhiều kết quả: bao nhiêu phương án (tránh tê liệt lựa chọn) · giúp so sánh theo mục tiêu · chống thiên kiến neo (bố cục lưới) · chọn hai bước (quét rồi so kỹ) · lưu/đánh dấu.
- Mức tham gia của AI: gợi ý (không đảm bảo được dùng) → tác vụ giới hạn → nhiều điểm chạm → đồng thiết kế từ đầu.

*Dùng cho hackathon:* §2.4 G7–G9, G15, G17; §4.2 validation — khi quan sát người thử, ghi các tín hiệu hai nghĩa ở trên thay vì chỉ hỏi "có thích không".

---

## 6 · Errors & graceful failures — Lỗi và thất bại êm

### 6.1 Hiểu "lỗi" và "thất bại"
- Lỗi là tất yếu. Hỏi: với từng nhóm người dùng, lỗi nghiêm trọng đến đâu? lỗi là do người dùng, hệ thống, hay lệch mục tiêu (alignment)? lỗi có nhìn thấy được không? có lỗi nền (background) nào không?
- True/false positive/negative — nhưng **mức nghiêm trọng do ngữ cảnh quyết định**, không do loại lỗi: false positive thường gây phiền/bỏ lỡ; false negative có thể để lọt điều quan trọng.
- Theo dõi log lỗi/null result, báo cáo người dùng; stress-test với edge case đã biết để viết thông báo lỗi và fallback.

### 6.2 Nguồn gốc lỗi
- **Lỗi dự đoán & dữ liệu huấn luyện:** dữ liệu kém/thiếu đại diện · chạm biên năng lực (thiếu dữ liệu) · train/tune chưa đủ.
- **Lỗi input & kỳ vọng:** người dùng yêu cầu ngoài phạm vi hoặc tưởng AI "hiểu" mọi thứ · thay đổi giao diện phá thói quen · một hành động bị đánh trọng số quá mức làm lệch toàn bộ.
- **Lỗi chất lượng/độ liên quan của output:** hoàn thành một phần do thiếu bộ nhớ/ngữ cảnh · kết quả tự tin nhưng trình bày không hợp nhu cầu.
- **Lỗi hệ thống nhiều tầng:** các hệ AI không "nói chuyện" với nhau.

*Dùng cho hackathon:* đối chiếu với **bốn lớp chỗ khó** của đề (①nguồn sự thật ②mơ hồ ③ngoài phạm vi ④đặc thù domain) — bốn nguồn lỗi của PAIR giúp nhóm tìm kịch bản cho mỗi lớp.

### 6.3 Đường đi tiếp sau thất bại
- Stakes cao thì cần kiểm tra an toàn thêm, giải thích giới hạn; kết quả "đơn giản" có thể không đủ.
- Thông báo lỗi **khiêm tốn, nói rõ giới hạn, cho bước tiếp theo** — ví dụ thay "Error" bằng "Bạn muốn 'rẻ' cỡ nào? Cho mình khoảng ngân sách hoặc xem [Bảng giá]".
- Nói trước về giới hạn khi dùng lần đầu; nhắc lại có kế hoạch; **tạo thói quen kiểm chứng** (nút "xem website", "xem đánh giá", RAG/trích dẫn).
- Thu phản hồi cả khi lỗi lẫn khi đúng; cho phép **người tiếp quản thủ công** với đủ ngữ cảnh; ghi lại vì sao AI không làm được để cải tiến.

*Dùng cho hackathon:* mỗi kịch bản trong §2.5 phải có "hành vi mong muốn" — hãy viết theo mẫu thông báo lỗi ở trên; golden set §2.6 cần ≥2 case cho mỗi nguồn lỗi.
