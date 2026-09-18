# Track C — Lesson Studio: AI cho đội sản xuất bài giảng

Năm đề dưới đây là bài toán thật của đội sản xuất bài giảng/video VLearn (Studio team), lấy từ Bộ đề Hackathon AI × Giáo dục của chương trình. Chúng nối thành một chuỗi: tài liệu thô → tri thức có cấu trúc → kịch bản → hình → phản hồi người học → phiên bản tiếp theo.

**Cách dùng trong mini-hackathon.** Mỗi đề gốc là một *sản phẩm hoàn chỉnh* với deliverable và rubric riêng — đó là **đích xa** để nhóm hiểu bài toán thật. Trong 3 buổi, nhóm **chọn một đề, cắt một lát cắt một câu** (một người dùng · một công việc · một quyết định AI · một kết quả), rồi đi đủ 5 tiêu chí nghiệm thu, spec, eval, validation như mọi track. Chấm theo `04-rubric.md`; rubric riêng của đề chỉ để biết người làm thật quan tâm gì.

**Người dùng của track này** là **Studio team** (đội sản xuất nội dung/video VLearn: người viết kịch bản, người dựng, biên tập) và **lab coach/giảng viên** — với C1 và C5 còn có chính người học.

**Chuẩn evidence riêng cho track C — ít hơn các track khác.** Người dùng là đội chuyên môn, số lượng ít, nên tiêu chí 2 áp dụng như sau: **phỏng vấn ≥3 người trong Studio team và/hoặc lab coach** theo Mom Test (guide §1.3), có log nguyên văn; **và/hoặc** mining tài liệu thật trong `data/vlearn-pack/` (transcript, slide) với số đếm + ví dụ. Không yêu cầu khảo sát 20 người. BTC sẽ bố trí đầu mối Studio team và lab coach để nhóm hẹn phỏng vấn — hỏi ở kênh chung. Với C1 và C5 có thể khảo sát thêm người học (cả lớp là người xem video thật).

**Data cho track này.** Sẵn có trong repo: transcript và slide bài giảng trong `data/vlearn-pack/`, và **`data/studio-pack/`** do Studio team cấp cho C3–C5 — mẫu kịch bản chung, kịch bản và video mẫu, lời đọc có mốc thời gian từng từ, hồ sơ nguồn mẫu, góp ý mẫu. Mục "Data & fixture" của từng đề ghi cụ thể có sẵn gì và đội tự dựng gì. Ban tổ chức chỉ cấp khung và ví dụ; dữ liệu để chạy và để tự chấm là việc của đội.

---

## C1 · Knowledge-to-Lesson — Graph tri thức và bài học thích ứng

**Người dùng.** Người viết nội dung/giảng viên (muốn quiz, lộ trình có căn cứ); người học (muốn lộ trình theo mình).

**Bối cảnh.** Slide và raw documents thường lặp ý, dùng tên gọi khác nhau cho cùng khái niệm, thiếu prerequisite hoặc thậm chí mâu thuẫn. Các công cụ sinh quiz/kịch bản trực tiếp từ tài liệu khó chỉ ra câu trả lời đến từ trang nào. Ở phía học viên, bài học thường được triển khai theo một lộ trình tuyến tính dù mỗi học viên đã nắm và đang gặp khó khăn ở những concept khác nhau.

**Bài toán gốc.** Hãy xây dựng một hệ thống biến slide và raw documents thành một mô hình tri thức có cấu trúc, trong đó các concept và quan hệ đều truy ngược được về nguồn. Từ mô hình này, hệ thống phải tạo được ít nhất một sản phẩm dạy học như quiz, kịch bản hoặc bài học tương tác. Nếu triển khai adaptive delivery, hệ thống cần theo dõi mastery theo concept, chọn nhánh học hoặc nội dung bổ trợ (remediation) và giải thích vì sao một học viên nhận được lộ trình đó.

Để giữ đề mở và vừa sức, đội được chọn một trong ba hướng triển khai: Graph-first — extraction, provenance và graph QA mạnh, kèm lesson đơn giản; Adaptive-first — dùng graph fixture do ban tổ chức cung cấp để tập trung vào learner model và branching; End-to-end — triển khai đầy đủ hai lớp ở mức hợp lý. Cả ba hướng được chấm trên cùng các tiêu chí đầu ra cốt lõi: nội dung có căn cứ, quyết định giải thích được và giáo viên có quyền kiểm soát.

**Lát cắt gợi ý cho hackathon** *(ví dụ cỡ, nhóm tự đặt câu của mình)*: *Một giảng viên · cần quiz cho một chương · AI trích 10 câu hỏi kèm trang nguồn · giảng viên duyệt/loại từng câu.* Hoặc adaptive-first: *một học viên · làm 5 câu · AI chọn nhánh ôn theo concept sai · giải thích vì sao.*

**Data & fixture.** 6 transcript (`[Txx-NNN]`) + 2 slide trong `data/vlearn-pack/` là tài liệu thô thật để extraction; chatlog VLearn cho thấy học viên hỏi ở trang/concept nào. Chưa có graph mẫu sẵn — graph-first tự extraction từ 1–2 transcript; adaptive-first tự dựng graph nhỏ 15–30 concept từ slide và ghi rõ là tự dựng.

**Deliverable đầy đủ** *(đích xa — không bắt buộc trong hackathon)*

**Deliverable Theo Path**
- Graph-first: graph explorer + provenance + graph QA + quiz/script cơ bản.
- Adaptive-first: lesson player/compiler + mastery model + branching + explainability, dùng fixture.
- End-to-end: ingestion → graph → output lesson thích ứng ở mức tối thiểu.


**Schema Cốt Lõi**
- Node: concept, definition, example, misconception, assessment item.
- Edge: prerequisite, broader/narrower, related, example-of, contradicts.
- Provenance: source file, page/slide, span, confidence.
- Learner state: mastery/confidence theo concept, event và quyết định branch.

**Không gian mở.**

- Graph DB, relational, JSON hoặc RDF.
- Rule, embedding, LLM hoặc hybrid extraction.
- Quiz, script, interactive video hoặc tutor.
- Bayesian knowledge tracing, rule mastery hoặc model tự thiết kế.
- Web, desktop, notebook hoặc plugin LMS.

**Demo bắt buộc của bản đầy đủ.** Nạp fixture hoặc graph chuẩn; chọn một concept; xem source/provenance; tạo quiz hoặc lesson; mô phỏng hai học viên có mastery khác nhau; giải thích từng nhánh và cho thấy khả năng tiếp tục phiên học từ trạng thái trước (resume). Đội graph-first có thể dùng branching đơn giản; đội adaptive-first không phải demo extraction.

**Rubric riêng của đề** *(tham khảo)*: Content/provenance correctness 25% · Core path quality 25% · Explainability & educator control 15% · Quiz/lesson usefulness 15% · Robustness 10% · UX/reproducibility 10%.

**Bonus.**

- Phát hiện knowledge gap/misconception.
- Graph diff khi tài liệu cập nhật.
- QTI/LMS export.
- Collaborative review.
- Adaptive chapters hoặc multimodal remediation.

**An toàn & đạo đức.**

- Không PII học viên thật.
- Provenance và uncertainty rõ ràng.
- Không tự xuất bản nội dung chưa duyệt.
- Giáo viên override được graph và lộ trình.

---

## C2 · Vietnamese Spoken-Script QA — Agent review kịch bản

**Người dùng.** Biên tập viên/người viết kịch bản video; giảng viên duyệt kịch bản.

**Bối cảnh.** Kịch bản tiếng Việt có thể đúng ngữ pháp nhưng vẫn khó nghe: dùng từ đúng từ điển nhưng sai sắc thái, câu mang cấu trúc dịch, nhiều danh từ trừu tượng, lặp ý, quá dài để đọc thành lời hoặc chứa số/acronym chưa được chuẩn hóa. Việc gắn nhãn chung là 'AI slop' không giúp biên tập viên biết cần sửa gì và dễ tạo false positive với văn bản do con người viết.

**Bài toán gốc.** Hãy xây dựng một agent QA cho kịch bản giáo dục tiếng Việt, có khả năng chỉ ra chính xác đoạn văn gây vấn đề, phân loại lỗi, giải thích vì sao câu sai nghĩa hoặc sượng khi đọc và đưa ra gợi ý sửa tối thiểu trước khi chuyển sang human review. Hệ thống phải phân biệt lỗi nội dung với lỗi chỉ liên quan đến cách đọc TTS, bảo toàn giọng tác giả và không tự động viết lại hoặc xuất bản toàn bộ tài liệu.

Không xây dựng 'máy đo xác suất văn AI'. Một từ, một cấu trúc hoặc một câu trơn tru không đủ để kết luận. Đội cần chứng minh reviewer đạt precision cao, kiểm soát tốt false positive trên văn bản do con người viết và có audit trail cho quyết định accept/reject của biên tập viên. Lời giải có thể dùng rule, LLM, classifier, read-aloud model, retrieval hoặc kết hợp.

**Lát cắt gợi ý cho hackathon** *(ví dụ cỡ, nhóm tự đặt câu của mình)*: *Một biên tập viên · duyệt một kịch bản 40 câu · AI chỉ đúng span sượng + lý do + gợi ý sửa tối thiểu · biên tập accept/reject từng chỗ.*

**Data & fixture.** Transcript bản sạch là văn nói thật của giảng viên (dùng làm chuẩn 'nghe được'); kịch bản lỗi để làm golden set nhóm tự viết/sinh và **gắn nhãn tay ≥10 case**, ghi rõ nguồn gốc. Phải có ≥1 đoạn văn người viết sạch để đo false positive.

**Deliverable đầy đủ** *(đích xa — không bắt buộc trong hackathon)*

**Taxonomy Tối Thiểu**
- Sai nghĩa/sai sắc thái từ.
- Translationese hoặc cú pháp sượng.
- Câu quá dài/breath-group overload.
- Lặp ý, filler, conclusion residue.
- Register/xưng hô không nhất quán.
- Claim thiếu căn cứ hoặc chứa chi tiết cụ thể không có nguồn.
- Số, acronym, URL, tên riêng và code-switch khó đọc.
- Pronunciation-only issue, tách khỏi semantic issue.


**Output Finding**
- Exact span.
- Category và severity.
- Giải thích gắn với ngữ cảnh.
- Confidence/uncertainty.
- Suggestion tối thiểu hoặc 'cần người xác minh'.
- Trạng thái human accept/reject và audit trail.

**Không gian mở.**

- Rule-based, LLM, classifier, RAG hoặc hybrid.
- Editor web, Word/Docs plugin, CLI hoặc API.
- Read-aloud/TTS preview.
- Personal style profile.
- Học từ feedback theo từng tổ chức.

**Demo bắt buộc của bản đầy đủ.** Review một kịch bản mới; lọc finding theo severity/category; mở giải thích; nghe bản đọc hoặc dùng chức năng read-aloud cho một câu sượng; accept/reject từng suggestion; xuất phiên bản đã được duyệt và audit report. BGK đưa thêm một đoạn sạch để kiểm tra false positive trực tiếp.

**Rubric riêng của đề** *(tham khảo)*: Span/category precision 25% · Recall trên lỗi quan trọng 15% · False-positive control 20% · Explanation quality 15% · Suggestion usefulness 10% · Human workflow 10% · Latency 5%.

**Bonus.**

- Read-aloud fluency score.
- Chuyển pronunciation issue sang TTS lexicon.
- Style profile theo giảng viên.
- Active learning từ accept/reject.
- So sánh nhiều phiên bản kịch bản.

**An toàn & đạo đức.**

- Không tự publish hoặc rewrite toàn bộ.
- Không dùng nhãn 'AI-generated' như kết luận về tác giả.
- Không lưu tài liệu ngoài scope.
- Không thêm claim mới không có nguồn.

---

## C3 · ScriptScout — Agent tự tìm tài liệu và viết kịch bản video có dẫn nguồn

**Người dùng.** Người viết kịch bản; giảng viên duyệt nguồn.

**Bối cảnh.** Muốn làm một video bài giảng thì trước hết phải có kịch bản, tức toàn bộ lời sẽ đọc trong video. Hiện nay người biên soạn phải tự đọc tài liệu, tự tra cứu trên mạng rồi tự viết. Việc này mất nhiều ngày, và khi đưa cho người khác duyệt thì không ai kiểm được câu nào lấy từ đâu, vì danh sách nguồn chỉ được liệt kê ở cuối tài liệu. Thiếu tư liệu thì người viết dễ đưa vào những con số hoặc ví dụ không có thật. Riêng chủ đề AI còn thay đổi từng tháng, nên một thông tin đúng lúc viết có thể đã cũ khi video lên sóng. Các công cụ "nghiên cứu sâu" hiện có viết được báo cáo dài, nhưng báo cáo để đọc bằng mắt khác hẳn kịch bản để đọc thành lời, chia theo từng cảnh và chỉ ra được từng câu dựa trên nguồn nào.

**Tóm tắt.** Đưa vào một chủ đề, nhận về kịch bản video mà mỗi câu đều truy được về nguồn.

**Bài toán gốc.** Hãy xây dựng một agent chỉ cần nhận bốn thông tin: chủ đề, mục tiêu bài học, người học là ai và video dài bao lâu — không đưa sẵn tài liệu nào. Agent tự đi tìm tài liệu trên mạng, tự đánh giá tài liệu nào đáng tin, rồi viết kịch bản.

Kết quả trả về gồm hai phần. Phần một là hồ sơ tài liệu: mỗi nguồn ghi rõ lấy ở đâu, ai viết, đăng ngày nào, đáng tin ở mức nào và vì sao, kèm đoạn trích được dùng làm bằng chứng; chỗ nào các nguồn nói khác nhau thì phải nêu ra. Phần hai là kịch bản viết đúng mẫu ban tổ chức đưa, trong đó mỗi câu có chứa thông tin, con số hay ví dụ thực tế đều bấm được để xem đoạn tài liệu gốc. Người duyệt xem hồ sơ tài liệu trước, bỏ nguồn nào thấy không ổn hoặc thêm nguồn của mình, rồi agent mới viết. Khi một nguồn bị bỏ, chỉ những câu dựa vào nguồn đó được viết lại, phần còn lại giữ nguyên.

Chỗ khó nhất của đề này là phân biệt "tìm được tài liệu" với "tài liệu đáng tin". Hệ thống phải nói rõ vì sao tin một nguồn, dựa trên những tiêu chí công bố trước. Số liệu quan trọng cần ít nhất hai nguồn độc lập xác nhận, nếu không thì phải đánh dấu là chưa kiểm chứng. Kịch bản phải là văn nói, đọc lên nghe tự nhiên, mỗi ý một cảnh, chứ không phải bản tóm tắt báo cáo. Ngoài các yêu cầu đó, đội thi tự chọn công cụ tìm kiếm, model AI và cách dựng agent.

**Phạm vi.** Đội thi chỉ cần làm ra kịch bản, không phải dựng thành video. Đội nào giải xong bài toán chính mà còn thời gian thì có thể dựng luôn một video từ chính kịch bản mình vừa tạo — đây là phần nâng cao, hoàn toàn không bắt buộc và không ảnh hưởng tới điểm của các tiêu chí chính.

**Lát cắt gợi ý cho hackathon** *(ví dụ cỡ, nhóm tự đặt câu của mình)*: *Một người viết · cần 5 câu mở đầu cho chủ đề X · AI tìm 3 nguồn, chấm tin cậy, viết 5 câu mỗi câu gắn nguồn · người viết loại một nguồn → chỉ câu phụ thuộc viết lại.*

**Data & fixture.** Không cần data pack — agent tự tìm web. `data/studio-pack/c3-scriptscout/` có mẫu kịch bản chung, một kịch bản thật 40 câu làm đích, hồ sơ nguồn mẫu và bảy câu đã nối vào nguồn, cùng 8 chủ đề để luyện. Đội tự dựng vài trang web cài bẫy để thử các chỗ khó.

**Deliverable đầy đủ** *(đích xa — không bắt buộc trong hackathon)*

**Sản phẩm tối thiểu**
- Agent chạy được trọn vẹn: nhập chủ đề, nhận về hồ sơ tài liệu và kịch bản.
- Hồ sơ tài liệu: mỗi nguồn ghi rõ lấy ở đâu, ai viết, đăng ngày nào, đáng tin tới đâu và vì sao.
- Kịch bản đúng mẫu, mỗi câu có thông tin đều dẫn được về nguồn.
- Màn hình duyệt nguồn: xem, bỏ, thêm nguồn và cho viết lại phần liên quan.
- Tự soát trích dẫn: đoạn trích phải khớp nội dung trang đã tải về, không phải do AI bịa.
- Xuất được kịch bản và hồ sơ tài liệu ra file.
- Đội tự chuẩn bị bộ trang web để thử các chỗ khó nêu dưới đây, và nộp kèm bài.
- Tài liệu hướng dẫn: cách chạy, chi phí mỗi lần chạy, và những gì hệ thống chưa làm được.

**Những chỗ sẽ khó**
- Trang web cài sẵn lệnh ẩn để lừa AI làm theo.
- Hai nguồn đều uy tín nhưng đưa số liệu khác nhau.
- Nguồn đã cũ hoặc đã có bản mới thay thế.
- Chủ đề gần như không có tài liệu tiếng Việt.
- Đường dẫn hỏng, hoặc trang bắt đăng nhập mới đọc được.

**Không gian mở.**

- Tìm kiếm bằng dịch vụ có sẵn, bằng tính năng tra web của model, bằng công cụ tự thu thập trang, hoặc kết hợp.
- Một agent làm hết, hoặc chia nhiều agent: đi tìm, thẩm định, viết, soát trích dẫn.
- Chấm độ tin cậy bằng bộ tiêu chí cứng, bằng AI, hoặc cả hai.
- Làm với nguồn tiếng Việt, tiếng Anh hoặc nhiều thứ tiếng.
- Giao diện: web, ứng dụng máy tính, hoặc chạy bằng dòng lệnh — đội tự chọn.

**Demo bắt buộc của bản đầy đủ.** Ban giám khảo đưa một chủ đề tại chỗ, kèm mục tiêu bài học và thời lượng. Đội nhập vào và cho xem quá trình hệ thống tìm rồi sàng lọc tài liệu. Mở hồ sơ tài liệu, bỏ một nguồn, chứng minh chỉ những câu liên quan được viết lại. Ban giám khảo chỉ bất kỳ một câu trong kịch bản, hệ thống phải mở đúng đoạn tài liệu chứng minh cho câu đó. Cuối cùng, đội cho chạy hai tình huống đã chuẩn bị sẵn — một trang có lệnh ẩn và hai nguồn nói ngược nhau — để thấy hệ thống phản ứng thế nào.

**Rubric riêng của đề** *(tham khảo)*: Câu truy được về nguồn và trích dẫn chính xác 25% · Chọn nguồn đáng tin, còn mới 20% · Kịch bản đọc lên nghe tự nhiên 20% · Người duyệt kiểm soát được, chỉ viết lại phần cần sửa 15% · Chịu được tình huống xấu 10% · Dễ dùng, chạy lại cho kết quả tương đương 10%.

**Bonus.**

- Chỉ ra chỗ các nguồn mâu thuẫn và trình bày để người duyệt chọn.
- Theo dõi nguồn đã dùng, báo khi nguồn đó có bản cập nhật.
- Tìm được ví dụ thực tế ở Việt Nam, có dẫn nguồn.
- Gợi ý cách hiện tên nguồn ngay trên màn hình video.
- So sánh mù: giấu nhãn, để người đọc chấm kịch bản của máy và của người cùng một chủ đề.
- NÂNG CAO (không bắt buộc): dựng luôn một video hoàn chỉnh từ chính kịch bản agent vừa viết.

**An toàn & đạo đức.**

- Không bịa nguồn, không bịa trích dẫn.
- Chữ trên trang web là dữ liệu để đọc, không phải lệnh để làm theo.
- Tôn trọng bản quyền và điều khoản của trang được lấy nội dung.
- Nói rõ chỗ nào chưa chắc chắn, chỗ nào còn nhiều quan điểm khác nhau.
- Kịch bản do AI viết phải có giảng viên duyệt trước khi dựng thành video.

---

## C4 · StoryboardAI — Agent dựng kịch bản hình ảnh cho video bài giảng

**Người dùng.** Người viết kịch bản; người dựng video hoặc coding agent; người duyệt.

**Bối cảnh.** Video bài giảng dạng đồ họa chuyển động cần một bản kế hoạch hình cho từng câu: câu này người xem nhìn thấy gì, sắp xếp ra sao, chữ nào hiện lên, hình chạy vào đúng lúc đọc tới từ nào. Hiện người viết kịch bản phải tự nghĩ ra rồi mô tả bằng lời cho bốn, năm chục câu mỗi video — phần việc chiếm nhiều thời gian nhất và cũng là chỗ đuối nhất. Người duyệt thì chỉ nhìn thấy hình khi cảnh đã dựng xong, mà dựng một video bằng AI mất hàng chục phút và tốn tiền, nên cảnh trống, hình lạc đề hay hình không nhất quán chỉ lộ ra ở phút cuối. Công cụ vẽ bằng AI hiện nay cho ra khung hình đẹp, nhưng mỗi khung một kiểu: một ký hiệu mang nghĩa ở phút đầu, tới phút sau đã thành thứ khác.

**Tóm tắt.** Đưa vào lời đọc của một video, nhận về kế hoạch hình cho từng câu kèm ảnh phác.

**Bài toán gốc.** Hãy xây dựng một agent nhận vào phần lời đọc đã chốt của một video — chia sẵn theo câu, kèm mốc thời gian của từng từ — rồi trả về bản kế hoạch hình cho cả video. Mỗi câu cần có đủ: người xem phải thấy ý gì, hình thể hiện ra sao, chữ gì hiện trên màn hình, hình chạy vào lúc đọc tới cụm từ nào, và một ảnh phác để người duyệt nhìn là hiểu ngay.

Phong cách hình ảnh do đội tự nghĩ ra. Không có thư viện hình hay bộ nhận diện nào bắt phải theo — nhưng đội phải khai phong cách của mình thành một sổ quy ước: màu nào mang nghĩa gì, ký hiệu nào chỉ cái gì, nhân vật nào xuất hiện thế nào. Hệ thống phải giữ đúng sổ quy ước của chính nó suốt cả video, và tự báo khi nó phá quy ước. Người duyệt góp ý cho một câu thì chỉ câu đó đổi, các câu khác giữ nguyên.

Chỗ khó nhất của đề này là tách "ý muốn truyền đạt" khỏi "cách vẽ ra": cùng một bản kế hoạch phải chuyển sang một phong cách khác được mà không mất ý. Hình chỉ được thể hiện những gì lời đọc có, không tự thêm con số, tên riêng hay kết quả mà kịch bản không nói. Ngoài các yêu cầu đó, đội thi tự chọn cách vẽ phác, cách dựng agent và giao diện duyệt.

**Phạm vi.** Đội thi chỉ cần làm ra kế hoạch hình, không phải dựng thành video. Đội nào giải xong bài toán chính mà còn thời gian thì có thể dựng luôn một video từ chính kế hoạch hình mình vừa tạo — đây là phần nâng cao, hoàn toàn không bắt buộc và không ảnh hưởng tới điểm của các tiêu chí chính.

**Lát cắt gợi ý cho hackathon** *(ví dụ cỡ, nhóm tự đặt câu của mình)*: *Một người viết · có lời đọc 10 câu · AI đề xuất ý cần thấy + hình + chữ trên màn hình cho từng câu · người viết góp ý một câu, chỉ câu đó đổi.*

**Data & fixture.** `data/studio-pack/c4-storyboardai/` có lời đọc 42 câu của một video thật kèm mốc thời gian từng từ, ba điều duy nhất được quy định về khung hình, và ba cảnh mẫu. Không có thư viện hình hay bộ nhận diện — phong cách là của đội, tự khai thành sổ quy ước. Đội chuẩn bị thêm ít nhất một video nữa để chạy thử (cắt ~40 câu từ transcript trong `data/vlearn-pack/` cũng được).

**Deliverable đầy đủ** *(đích xa — không bắt buộc trong hackathon)*

**Sản phẩm tối thiểu**
- Agent chạy được trọn vẹn: nhập lời đọc, nhận về kế hoạch hình cho cả video.
- Mỗi câu một cảnh, có ảnh phác nhìn là hiểu.
- Sổ quy ước hình ảnh do đội tự định nghĩa, và hệ thống giữ đúng nó suốt video.
- Bảng duyệt; góp ý một câu thì chỉ câu đó vẽ lại.
- Tự soát: báo khi một cảnh phá quy ước của chính đội.
- Chạy được trên ít nhất hai bộ lời đọc: file mẫu ban tổ chức cấp và một video do đội tự chuẩn bị.
- Tài liệu hướng dẫn: cách chạy, chi phí và những gì hệ thống chưa làm được.

**Khung hình ban tổ chức quy định**
- Khung 1920×1080, 30 hình mỗi giây.
- Nội dung dạy học nằm trong vùng an toàn; dải dưới cùng để trống cho phụ đề.
- Chữ trên màn hình tối đa 40 ký tự.

Ngoài ba điều này, mọi thứ về hình là của đội.

**Những chỗ sẽ khó**
- Câu trừu tượng, không có vật gì cụ thể để vẽ.
- Câu nhồi quá nhiều ý so với thời gian đọc.
- Một khái niệm nhắc lại sau vài phút, phải vẽ giống lần trước.
- Đổi phong cách giữa chừng mà không mất ý.
- Lời đọc ám chỉ có số liệu nhưng không nêu con số nào.

**Không gian mở.**

- Phong cách hình hoàn toàn tự chọn: sơ đồ, minh hoạ, ảnh, chữ động, hay trộn nhiều kiểu.
- Vẽ phác bằng AI sinh ảnh, bằng hình vector do AI viết, bằng khung xám đơn giản, hay dựng bằng mã.
- Lên khung cả video trước rồi mới chi tiết từng câu, hoặc làm ngược lại.
- Góp ý bằng chữ, bằng giọng nói, bằng khoanh vùng trên ảnh, hoặc chọn giữa vài phương án được đề xuất.
- Giao diện: bảng duyệt trên web, ứng dụng máy tính, hoặc chạy bằng dòng lệnh — đội tự chọn.

**Demo bắt buộc của bản đầy đủ.** Nạp lời đọc của một video và dựng kế hoạch hình cho cả video, rồi mở bảng duyệt. Chạy hai lần: một lần trên file mẫu ban tổ chức cấp, một lần trên video do đội tự chuẩn bị. Đội trình bày sổ quy ước hình ảnh của mình, rồi chỉ ra ít nhất hai quy ước được giữ giống nhau từ đầu đến cuối video. Gõ một câu góp ý cho một cảnh và cho thấy chỉ cảnh đó đổi. Đổi phong cách cho một đoạn và cho thấy ý vẫn nguyên. Ban giám khảo chọn một câu trừu tượng để xem hệ thống minh họa thế nào khi không có vật gì cụ thể để vẽ.

**Rubric riêng của đề** *(tham khảo)*: Hình phục vụ đúng ý dạy học 25% · Nhất quán xuyên suốt video 20% · Đổi phong cách mà giữ nguyên ý 15% · Dựng được thành cảnh thật 15% · Sửa từng phần và trải nghiệm duyệt 15% · Chịu được tình huống xấu 10%.

**Bonus.**

- Đề xuất vài phương án hình cho một câu để người duyệt chọn.
- Ghép ảnh phác với giọng đọc thành bản nháp chạy đúng thời lượng để xem thử.
- Phát hiện chỗ hình cần số liệu mà kịch bản chưa cung cấp.
- Không truyền đạt thông tin chỉ bằng màu, để người khó phân biệt màu vẫn hiểu.
- NÂNG CAO (không bắt buộc): dựng luôn một video hoàn chỉnh từ chính kế hoạch hình vừa tạo.

**An toàn & đạo đức.**

- Không thêm số liệu, tên riêng hay logo mà kịch bản không có.
- Không dùng logo, giao diện sản phẩm, nhân vật có bản quyền hay ảnh người thật khi chưa được phép.
- Tránh định kiến khi vẽ con người (giới tính, vùng miền, nghề nghiệp).
- Ví dụ tự nghĩ ra phải ghi rõ là hình minh họa.

---

## C5 · FeedbackRadar — Agent biến góp ý của người học thành bản sửa video

**Người dùng.** Đội sản xuất video; giảng viên; gián tiếp là người học (người gửi phản hồi).

**Bối cảnh.** Sau mỗi đợt học, góp ý về video bài giảng đến từ nhiều nơi: phiếu khảo sát, bình luận, tin nhắn của người học và của giảng viên, trợ giảng. Góp ý thường mơ hồ ("đoạn giữa hơi nhanh", "phần token khó hiểu"), có khi trái ngược nhau, có khi mười người cùng nói một điều, và lẫn lộn giữa lỗi nội dung với lỗi kỹ thuật như tiếng nhỏ hay phụ đề sai. Đội sản xuất đọc tay từng góp ý rồi tự quyết định sửa gì, và thường làm lại gần như cả video dù chỉ vài câu có vấn đề. Quy trình làm loại video này là thu giọng trước rồi dựng hình khớp theo độ dài giọng, nên đổi lời một câu kéo theo phải thu lại giọng câu đó và dựng lại cảnh đó. Vì vậy, chỉ ra đúng và ít chỗ cần sửa tiết kiệm được rất nhiều thời gian và tiền.

**Tóm tắt.** Đưa vào góp ý của người học, nhận về danh sách vấn đề đã chỉ rõ nằm ở phút nào và kế hoạch sửa cho phiên bản sau.

**Bài toán gốc.** Hãy xây dựng một agent nhận vào góp ý từ nhiều kênh (bình luận, tin nhắn, bảng khảo sát) cùng bản chép lời có mốc thời gian và kịch bản của video hiện tại, rồi trả về kế hoạch sửa cho phiên bản sau.

Hệ thống cần gom những góp ý nói cùng một chuyện thành một vấn đề, chỉ ra vấn đề đó nằm ở câu nào và phút thứ mấy, xếp loại (nội dung sai, khó hiểu, nhịp nhanh chậm, giọng đọc, hình ảnh, lỗi kỹ thuật), rồi sắp thứ tự ưu tiên theo mức ảnh hưởng và số người nhắc tới. Với mỗi vấn đề, hệ thống đề xuất cách sửa ít tốn nhất và nói rõ phải làm lại những gì: câu nào phải thu lại giọng, cảnh nào phải dựng lại. Người duyệt phải đi được từ một vấn đề tới đúng đoạn video và tới những góp ý gốc đã tạo ra vấn đề đó, rồi đồng ý hoặc bỏ từng đề xuất.

Chỗ khó nhất của đề này là phải có bằng chứng: mỗi vấn đề nêu ra đều phải chỉ được ra những góp ý nào tạo nên nó, và ý kiến của một người không được thổi thành vấn đề chung. Trọng tâm là hiểu người học nói gì và sửa đúng chỗ, không phải soát lại toàn bộ kịch bản. Ngoài các yêu cầu đó, đội thi tự chọn cách gom nhóm góp ý, cách định vị vào video, cách xếp ưu tiên và giao diện duyệt.

**Phạm vi.** Đội thi chỉ cần làm ra kế hoạch sửa và bản kịch bản phiên bản mới, không phải dựng thành video. Đội nào giải xong bài toán chính mà còn thời gian thì có thể dựng luôn phiên bản video mới từ chính kế hoạch sửa của mình — đây là phần nâng cao, hoàn toàn không bắt buộc và không ảnh hưởng tới điểm của các tiêu chí chính.

**Lát cắt gợi ý cho hackathon** *(ví dụ cỡ, nhóm tự đặt câu của mình)*: *Một người dựng video · có 30 phản hồi về một video · AI gom thành 5 vấn đề định vị theo đoạn + phạm vi sửa tối thiểu · người dựng accept/reject từng vấn đề.*

**Data & fixture.** `data/studio-pack/c5-feedbackradar/` có video thật 4 phút đang bị góp ý, kịch bản 40 câu của nó, bảng câu ↔ mốc thời gian, bản chép lời, 18 góp ý mẫu và một kết quả mẫu. Bộ góp ý để chạy và để tự chấm (khoảng 100, kèm đáp án) do đội tự chuẩn bị — thu thật bằng khảo sát bạn cùng lớp về video này càng tốt (vừa là data, vừa là evidence tiêu chí 2); phần tự viết thêm phải gắn nhãn.

**Deliverable đầy đủ** *(đích xa — không bắt buộc trong hackathon)*

**Sản phẩm tối thiểu**
- Nhận được ít nhất hai dạng góp ý: văn bản (bình luận, tin nhắn) và bảng khảo sát.
- Xóa thông tin cá nhân trước khi đưa vào phân tích.
- Danh sách vấn đề, mỗi vấn đề dẫn ngược được về những góp ý gốc tạo ra nó.
- Định vị vấn đề về đúng câu và đúng phút; bấm vào là phát đúng đoạn video.
- Kế hoạch sửa: đổi gì ở câu nào, phải thu lại giọng mấy câu, dựng lại mấy cảnh.
- Đồng ý hoặc bỏ từng đề xuất, rồi xuất ra kịch bản phiên bản mới theo mẫu kịch bản chung.
- Đội tự chuẩn bị bộ dữ liệu khoảng một trăm góp ý kèm đáp án, có đủ các chỗ khó nêu dưới đây.
- Báo cáo tự chấm hệ thống trên chính bộ dữ liệu đó, và nộp cả bộ dữ liệu lẫn đáp án kèm bài.

**Những chỗ sẽ khó**
- Góp ý mơ hồ, không nói rõ chỗ nào.
- Hai nhóm người nói ngược nhau về cùng một đoạn.
- Một người gửi đi gửi lại nhiều lần cùng một ý.
- Góp ý cài lệnh ẩn để lừa AI.
- Lời công kích cá nhân.
- Lỗi kỹ thuật (tiếng nhỏ, phụ đề sai) trộn lẫn với góp ý về nội dung.

**Không gian mở.**

- Gom nhóm góp ý bằng AI, bằng thuật toán gom cụm, bằng mô hình chủ đề, hoặc kết hợp.
- Định vị vào video bằng tìm theo ngữ nghĩa trên bản chép lời, bằng khớp từ khoá, hoặc bằng mốc thời gian có sẵn.
- Xếp ưu tiên theo mức ảnh hưởng so với chi phí, theo bộ tiêu chí cứng, hoặc học dần từ quyết định của người duyệt.
- Dùng thêm dữ liệu hành vi xem (chỗ hay tua lại, chỗ bỏ ngang) nếu đội tự tạo được dữ liệu mô phỏng.
- Giao diện: web, ứng dụng máy tính, hoặc chạy bằng dòng lệnh — đội tự chọn.

**Demo bắt buộc của bản đầy đủ.** Nạp bản chép lời và kịch bản ban tổ chức cấp, cùng bộ góp ý do đội tự chuẩn bị. Hệ thống hiển thị danh sách vấn đề đã xếp ưu tiên. Mở một vấn đề, phát đúng đoạn video và xem những góp ý gốc tạo ra nó. Đồng ý một đề xuất, rồi xuất kịch bản mới kèm danh sách những gì phải làm lại. Ban giám khảo thêm tại chỗ một nhóm góp ý trái chiều hoặc một góp ý cài lệnh ẩn để xem hệ thống xử lý thế nào.

**Rubric riêng của đề** *(tham khảo)*: Tìm đúng và đủ vấn đề 25% · Định vị đúng câu, đúng phút 20% · Kế hoạch sửa gọn, đúng phạm vi 20% · Vấn đề nào cũng dẫn được về góp ý gốc 15% · Người duyệt làm việc thuận tay 10% · Chịu được tình huống xấu và bảo vệ thông tin cá nhân 10%.

**Bonus.**

- Theo dõi một vấn đề qua nhiều phiên bản video xem đã sửa dứt điểm chưa.
- Ước tính chi phí có tính cả ảnh hưởng dây chuyền sang câu liền kề.
- Kết hợp thêm dữ liệu hành vi xem.
- Tự tách góp ý về nội dung khỏi góp ý về kỹ thuật để chuyển đúng người phụ trách.
- Học từ những đề xuất mà đội sản xuất đã đồng ý hoặc đã bỏ.
- NÂNG CAO (không bắt buộc): dựng luôn phiên bản video mới từ chính kế hoạch sửa đã được duyệt.

**An toàn & đạo đức.**

- Không dùng thông tin cá nhân của học viên thật; ẩn danh trước khi gửi cho AI.
- Không để ý kiến số đông che mất một góp ý ít người nói nhưng quan trọng.
- Lọc lời công kích cá nhân, không trích nguyên văn vào báo cáo.
- Góp ý là dữ liệu để đọc, không phải lệnh để làm theo.
- AI chỉ đề xuất; người duyệt quyết định mọi thay đổi.

---
