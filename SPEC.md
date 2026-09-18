<!-- # [HƯỚNG DẪN CHUNG]: Chọn đúng hướng thi (A, B, C) và loại dự án (Tối ưu tính năng có sẵn hay Tính năng mới) -->
# AI SPEC — Tối ưu hóa Trợ lý học tập VLearn (Global Multi-day Tutor & Dynamic Mindmap) · Nhóm GoldDuck · Zone C5
Hướng: [x] A — VLearn  [ ] B — Trợ lý Học viên  [ ] C — Làn mở
Loại: [x] Tối ưu tính năng có sẵn  [ ] Tính năng mới

<!-- # [GIẢI THÍCH §1]: 
# - Job executor + workflow: Ai là người dùng chính? Họ đang làm việc gì thực tế, từng bước gặp khó khăn ra sao?
# - Core JTBD: Việc cốt lõi họ cần làm xong là gì? (LƯU Ý: Không nhắc tên công nghệ/AI ở câu này).
# - Problem statement: Nỗi đau/tổn thất thời gian thực tế của họ là gì? (LƯU Ý: Không nhắc tên công nghệ/AI).
# - Evidence: Bằng chứng số liệu khảo sát thật (n=?, % tỷ lệ từng câu hỏi) và >=5 câu nói bức xúc nguyên văn kèm mã định danh.
-->
## §1. User & Job
- Job executor + workflow: Học viên khóa K4 Lớp 3B làm bài Lab tổng hợp tại phòng E402/E403 (workflow: Làm Lab -> Cần tra cứu kiến thức cũ -> Mở VLearn -> Quên vị trí Day/slide -> Phải thoát ra mở từng Day để hỏi bot cục bộ -> Bot trả lời sai ngữ cảnh chéo ngày hoặc trỏ nhầm nguồn -> Mất mạch tư duy làm bài).
- Core JTBD: Tra cứu, đối chiếu và xâu chuỗi chính xác kiến thức đã học qua nhiều ngày một cách nhanh chóng để giải quyết bài tập thực hành mà không bị gián đoạn tiến độ.
- Problem statement: Người học mất từ 3 đến hơn 10 phút mở từng bài học riêng biệt để tìm lại kiến thức cũ do hệ thống phân mảnh nội dung theo từng ngày và bot hiện tại không hỗ trợ tra cứu chéo buổi học.
- Evidence:
  - Kết quả khảo sát (n = 25 học viên thực tế):
    - 92% (23/25) có nhu cầu tìm lại nội dung đã học trong 7 ngày qua.
    - 84% (21/25) xác nhận ngại việc phải bấm qua nhiều bước từ trang chủ/khóa học để vào mở bot (28% thường xuyên, 56% thỉnh thoảng).
    - 76% (19/25) mất từ 3 đến hơn 10 phút khi tìm lại kiến thức cũ (56% mất 3-10 phút, 20% mất trên 10 phút, 8% bỏ cuộc sang hỏi bạn bè hoặc Google/ChatGPT).
    - 100% (25/25) KHÔNG nhớ chính xác vị trí slide/video của kiến thức (72% chỉ nhớ Day nhưng không nhớ vị trí, 28% hoàn toàn không nhớ nội dung nằm ở Day nào).
    - 72% (18/25) gặp rào cản với bot cục bộ (44% đã thử hỏi kiến thức Day trước và bot trả lời sai/báo không có thông tin; 28% chưa từng thử vì nghĩ bot Day nào chỉ biết Day đó).
    - 64% (16/25) xác nhận từng thấy AI trên VLearn trích dẫn sai nguồn/sai vị trí slide hoặc video (20% gặp thường xuyên, 44% thỉnh thoảng).
  - Mining dữ liệu truy vấn thực tế: Ghi nhận 7 case câu hỏi không rõ ràng/uncertain cần làm rõ ngữ cảnh.
  - ≥5 quote/ví dụ nguyên văn (mã học viên định dạng mẫu 2A2026xxxxx):
    1. "Cần dùng lại khái niệm Prompt của Day 1 khi làm Lab Day 3 mà bot Day 3 báo không có thông tin, phải mở tab mới vào Day 1 rất phiền." — HV-2A2026xxxxx.
    2. "Lúc làm bài tập không nhớ nổi cái sơ đồ nằm ở Day 1 hay Day 2, bấm vào từng Day lật từng trang slide mất gần 10 phút." — HV-2A2026xxxxx.
    3. "Bấm vào link slide do AI dẫn kèm toàn bị trỏ lệch trang hoặc nhảy sang bài khác không liên quan." — HV-2A2026xxxxx.
    4. "Đang ở trang Khóa học của tôi muốn hỏi luôn mà cứ phải click Khóa học -> Day -> mở chat, quá nhiều bước thừa." — HV-2A2026xxxxx.
    5. "Cứ tưởng bot ở Day nào thì chỉ được hỏi bài Day đó, không nghĩ nó trả lời được câu hỏi tổng hợp nhiều ngày." — HV-2A2026xxxxx.

<!-- # [GIẢI THÍCH §2]: 
# - So sánh 3 phương án/ý tưởng giải pháp mà nhóm từng cân nhắc.
# - Nêu rõ lý do LOẠI các ý tưởng khác và lý do CHỌN giải pháp hiện tại.
-->
## §2. Impact & quyết định chọn
- Bảng impact ≥3 ứng viên (so sánh các phương án giải pháp nhóm cân nhắc):

| Ứng viên tính năng | Bao nhiêu người | Tần suất | Tốn gì mỗi lần | Khả thi kỹ thuật |
|---|---|---|---|---|
| 1. Sơ đồ Mindmap đồ họa tĩnh toàn khóa | ~100 học viên | 1 lần/tuần (khi ôn tập) | 15-20 phút đọc hiểu | Trung bình (cồng kềnh, không gắn liền ngữ cảnh tra cứu) |
| 2. Bộ tạo câu hỏi trắc nghiệm ôn tập đa Day | ~100 học viên | 2-3 lần/tuần | 10 phút làm bài | Cao (chỉ giải quyết kiểm tra thụ động) |
| 3. Tối ưu Bot VLearn: Global Multi-day + Citation + Dynamic Mindmap (2 luồng) + Fallback thông minh | ~100 học viên | 5-10 lần/buổi thực hành | 3-10 phút mò mẫm/lần | Rất cao (RAG đa tài liệu + Metadata Filter + Hybrid Search + Template offline) |

- Ứng viên ĐÃ LOẠI:
  - Sơ đồ tĩnh toàn khóa: Loại vì học viên không cần sơ đồ chung chung quá rộng, mà cần sơ đồ liên kết trực tiếp theo bài học hoặc chủ đề đang hỏi.
  - Bộ Quiz trắc nghiệm: Loại vì không giải quyết bài toán cấp bách khi học viên đang bị tắc nghẽn ở bài Lab.
- Ứng viên CHỌN: Gói tối ưu hóa Chatbot VLearn toàn diện (Global Multi-day Tutor kết hợp Dynamic Mindmap có highlight bbox, Grounded Abstention và Ambiguity Disambiguation). Giúp tiết kiệm thời gian tra cứu cho 76% học viên và xử lý triệt để 64% lỗi trích dẫn sai nguồn.

<!-- # [GIẢI THÍCH §3]: 
# - Phân tích >=2 sản phẩm ngoài thị trường cùng giải quyết việc tìm kiếm tài liệu.
# - Nêu rõ: Luồng đi (Flow), Điểm đáng học, Điểm đáng né, và Nhóm mình khác gì họ.
-->
## §3. Giải pháp tương tự đã nghiên cứu
- Notion AI Q&A:
  - Flow: Ô tìm kiếm toàn cục ở navigation bar -> Truy vấn trên mọi trang workspace -> Trả lời kèm trích dẫn văn bản nguồn.
  - Đáng học: Cho phép tìm kiếm toàn cục mà không bắt người dùng tự định vị thư mục.
  - Đáng né: Chỉ trỏ về trang cha, không dẫn sâu vào đúng block/đoạn cụ thể.
  - Mình khác gì: Trỏ chính xác đến từng file PDF slide, số trang và highlight đúng khối văn bản (bbox) của từng Day.
- Google NotebookLM:
  - Flow: Người dùng tải tài liệu vào notebook -> Chatbot trả lời dựa trên tài liệu kèm đánh số trích dẫn footnote -> Bấm trích dẫn tự cuộn đến đúng đoạn trong PDF.
  - Đáng học: Trích dẫn cực kỳ minh bạch, người học kiểm chứng được ngay bằng chứng nguyên văn.
  - Đáng né: Bắt người dùng phải tự tải tài liệu thủ công, không nhúng trực tiếp vào luồng học tập của hệ thống LMS.
  - Mình khác gì: Được tích hợp sẵn ngữ liệu chuẩn hóa toàn khóa học VLearn ngay tại trang chủ, đồng thời sinh sơ đồ Mindmap đóng vai trò lớp điều hướng (navigation layer) trực tiếp trên slide gốc.

<!-- # [GIẢI THÍCH §4]: 
# - Lát cắt MỘT CÂU: Công thức chuẩn: 1 User + 1 Việc làm + 1 Quyết định của AI + 1 Kết quả đạt được.
# - Non-goals: Liệt kê >=3 thứ nhóm TỪ CHỐI làm để tránh bị loãng scope.
# - Mức prototype: Working (chỉ rõ cái nào mock là giao diện, cái nào thật là code backend/AI).
# - Automation: Augment (trợ lực cho người) hay Automate (tự động thay người hoàn toàn)?
# - Nguyên tắc HAX/PAIR: Áp dụng các nguyên tắc thiết kế AI nào vào chi tiết nào của app.
-->
## §4. Thiết kế
- Lát cắt MỘT CÂU: Học viên nhập câu hỏi tra cứu hoặc yêu cầu ôn tập tại trang chủ VLearn, AI tự động truy xuất tài liệu từ tất cả các Day đã học để trả lời tổng hợp kèm trích dẫn số trang slide, đồng thời sinh sơ đồ tư duy động (Dynamic Mindmap gắn tọa độ bbox) và điều hướng gợi ý khi câu hỏi mơ hồ hoặc thiếu nguồn.
- Non-goals:
  - KHÔNG cho phép AI tự do bịa từ ngữ hoặc nguồn mới trong Mindmap (chỉ được gom nhóm các node/evidence_id thật có sẵn từ slide).
  - KHÔNG dùng LLM để sinh câu hỏi phân loại khi người dùng hỏi mơ hồ (bắt buộc dùng template offline để kiểm soát chi phí).
  - KHÔNG tự động giải hộ toàn bộ mã nguồn bài Lab cho học viên.
  - KHÔNG thay thế việc đọc tài liệu gốc (chỉ tóm tắt, trích xuất căn cứ và highlight slide để học viên tự học).
- Mức prototype nhắm tới: [x] Working
  - Phần mock: Khung giao diện nhúng tại màn hình khóa học VLearn.
  - Phần thật: Backend FastAPI, Pipeline Hybrid Search (BM25 + Dense `multilingual-e5-small` qua RRF, Metadata Filtering theo `--day`), OpenAI API, cơ chế tính top concept gần nhất bằng TF-IDF/local keyword khi từ chối, và bộ render SVG bezier curve nối trực tiếp tọa độ DOM thực tế.
- Automation: [x] Augment
  - Lý do theo cost-of-error: Chi phí sai lệch kiến thức kỹ thuật rất lớn. AI chỉ đóng vai trò trợ lực tóm tắt và trỏ bằng chứng nguyên văn kèm vị trí highlight bbox, học viên là người trực tiếp đọc lại slide để xác nhận và áp dụng vào bài làm.
- §4b. Nguyên tắc đã áp dụng:
  | Nguyên tắc | Áp cụ thể vào đâu trong prototype |
  |---|---|
  | HAX G1 (Làm rõ AI có thể làm gì) | Placeholder ghi rõ: "Hỏi đáp kiến thức tổng hợp từ Day 01 đến Day 03 hoặc yêu cầu ôn tập theo chủ đề/buổi học kèm trích dẫn slide". |
  | HAX G9 (Minh bạch nguồn gốc) | Mọi luận điểm bắt buộc đính kèm thẻ nguồn: `[Tên file slide - Trang X]`, click node mindmap tự cuộn và tô vàng khối văn bản trên slide PDF. |
  | HAX G11 (Thừa nhận khi không chắc chắn) | Khi không tìm thấy nguồn, AI từ chối trả lời nhưng hiển thị top concept/source gần nhất từ retriever thay vì báo lỗi cụt ngủn. |
  | PAIR (Feedback & Control) | Khi câu hỏi thiếu ngữ cảnh, bật template offline hỏi lại: "Bạn muốn hỏi về [Transformer], [Attention] hay [chủ đề khác]?" để học viên tự chọn. |

<!-- # [GIẢI THÍCH §5]: 
# - Lập bảng >=8 kịch bản kiểm thử các ca khó/ca biên mà AI thường hay gặp lỗi.
# - Cột cuối cùng phải ghi rõ hành vi AI cần xử lý chuẩn là gì.
-->
## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản (≥8)
| STT | Tên kịch bản | Lớp khó | Mô tả đầu vào | Hành vi AI mong muốn |
|---|---|---|---|---|
| 1 | Câu hỏi chéo 2 Day | Multi-hop | "So sánh Prompt Engineering ở Day 1 với ReAct Prompt ở Day 3" | Tổng hợp cả 2 nguồn, nêu rõ điểm giống/khác kèm 2 citation riêng biệt của Day 1 và Day 3. |
| 2 | Mindmap theo bài học (Buổi N) | Synthesis / Structural | Bấm nút hoặc gõ "Tạo mindmap buổi 2" | Tự động gom các heading slide thành các nhánh lớn, gán đúng tọa độ bbox để click node là highlight đúng trang slide PDF. |
| 3 | Mindmap theo chủ đề chéo Day | Cross-day Synthesis | "Tạo mindmap về RAG" | Truy xuất bằng chứng từ nhiều Day bằng Hybrid Search + RRF, gom nhóm concept và bắt buộc mỗi node lá phải trỏ đúng 1 evidence_id thật. |
| 4 | Không tìm thấy nguồn (Abstention) | Grounded Abstention | Hỏi một khái niệm không có trong bài giảng (VD: "Q-learning") | Từ chối trả lời nội dung chính, nhưng hiển thị top concept gần nhất từ retriever (VD: Attention, Multi-head attention) qua thuật toán local (0 lần gọi AI). |
| 5 | Câu hỏi mơ hồ thiếu ngữ cảnh | Ambiguity Disambiguation | Gõ cộc lốc: "Cái này chạy thế nào?" | Kích hoạt template offline: "Bạn muốn hỏi về [Transformer], [Attention] hay [chủ đề khác]?" mà không đổi intent thành câu hỏi khác. |
| 6 | Trích dẫn sai trang | Citation Accuracy | Hỏi về thuật ngữ chỉ có ở 1 slide duy nhất (VD: Temperature) | Trả lời ngắn, cite chính xác số trang slide đó, không trích dẫn lan man sang các trang lân cận. |
| 7 | Rò rỉ metadata theo Day | Metadata Leaking | Câu hỏi truyền `--day D01` nhưng retriever lại bốc tài liệu từ Foundation/T06 | Bộ lọc metadata phải chặn cứng, chỉ lấy dữ liệu thuộc đúng Day được yêu cầu. |
| 8 | Lỗi sinh cấu trúc / Không có API key | Algorithm Fallback | Gọi tạo mindmap khi mất mạng/lỗi JSON/không có API key | Không làm ứng dụng bị treo; tự động fallback gom nhóm bằng Cosine Similarity hoặc cấu trúc Agenda. |

<!-- # [GIẢI THÍCH §6]: 
# - Mô tả 4 luồng người dùng trải nghiệm: 
#   + Happy path (luồng chuẩn hoàn hảo).
#   + Low-confidence (khi AI không chắc chắn).
#   + Failure / Abstention (khi không tìm thấy gì).
#   + Correction (khi câu hỏi mơ hồ hoặc người dùng muốn sửa/làm rõ).
-->
## §6. Bốn đường đi của trải nghiệm
- Happy path: 
  + Tra cứu: Học viên gõ câu hỏi tổng hợp tại trang chủ -> AI trả lời tóm tắt trong < 3 giây kèm các thẻ link trích dẫn đúng slide và số trang -> Học viên click mở đúng slide gốc để học.
  + Mindmap: Học viên yêu cầu tạo mindmap theo bài hoặc theo chủ đề -> Hệ thống render sơ đồ SVG trực tiếp -> Click node nào thì màn hình PDF tự động cuộn đến đúng trang và tô vàng (highlight bbox) khối văn bản đó.
- Low-confidence: AI tìm thấy tài liệu có độ tương đồng thấp -> Phản hồi: "Tài liệu Day 1-3 chỉ đề cập sơ lược nội dung này tại [Slide X, Trang Y]..." kèm cảnh báo độ khớp không tuyệt đối.
- Failure/không căn cứ (Grounded Abstention): Khi không tìm thấy nguồn, câu trả lời từ chối không cụt ngủn mà hiển thị ngay top concept hoặc source gần nhất từ retriever (ví dụ: gợi ý về Attention mechanism hoặc Multi-head attention) để hỗ trợ học viên tiếp tục tìm kiếm. Chi phí: 0 lần gọi AI (dùng local keyword/TF-IDF).
- Correction (Ambiguity Disambiguation): Khi câu hỏi thiếu chủ đề hoặc ngữ cảnh khiến Tutor phải đoán ý, hệ thống dùng template offline để làm rõ tham số còn thiếu: "Bạn muốn hỏi về [Transformer], [Attention] hay [chủ đề khác]?" (các lựa chọn không làm đổi intent gốc). Chi phí: Tối đa 1 lần gọi AI sau khi người học chọn chủ đề, không dùng LLM để sinh thêm câu hỏi phân loại trước đó.
- Khi bị đòi ngoài phạm vi: Yêu cầu giải hộ code bài Lab -> AI chỉ trích xuất quy tắc, bước thực hiện và công thức từ slide, từ chối làm bài nộp thay.
- Case đặc thù domain: Học viên dùng các thuật ngữ viết tắt (ReAct, LLM, RAG, FT) -> Retriever tự động chuẩn hóa về đúng thực thể trong tài liệu slide để truy xuất chuẩn xác.

<!-- # [GIẢI THÍCH §7]: 
# - Chiều chất lượng: Nêu rõ tiêu chí đo lường (Độ bám tài liệu, Độ đúng của trích dẫn, Khả năng xử lý biên).
# - Golden set: Bộ 20 case test lưu trong repo.
# - Quality bar: Mức % bắt buộc phải đạt khi thi đấu.
# - Bảng các lượt chạy: Ghi nhận số liệu test thật qua từng lần chạy code (chỉ rõ vì sao rớt).
-->
## §7. Kiểm thử
- Chiều chất lượng + định nghĩa kiểm chứng được:
  1. Trả lời có căn cứ (Groundedness): Câu trả lời và các node Mindmap phải bám sát nội dung slide/transcript, 100% node lá phải validate khớp với evidence_id thật và có tọa độ bbox hợp lệ.
  2. Độ chính xác trích dẫn (Citation Accuracy): Citation đúng và tồn tại trong context, không bịa nguồn, trỏ đúng file và số trang.
  3. Khả năng xử lý biên (Abstention & Disambiguation): Thiếu dữ liệu hoặc ngoài phạm vi phải biết từ chối/gợi ý concept gần nhất; câu hỏi mơ hồ phải kích hoạt template phân loại thay vì đoán mò.
- Golden set: Gồm 20 case kiểm thử theo kịch bản chuẩn hóa (Đơn Day, Chéo Day, Ôn tập chủ đề, Out-of-scope, Ambiguous case) lưu tại `eval/golden_set.json`.
- Quality bar: "Đạt khi ≥ 80% (16/20 case) qua bộ kiểm thử, trong đó Citation Accuracy đạt 100% trên các case trả lời thành công, 100% case ngoài phạm vi từ chối chính xác và xử lý đúng kịch bản phân loại/gợi ý gần nhất qua AI call thật (không dùng câu trả lời gán cứng)."
- Kết quả các lượt chạy:
  | Lượt chạy | Ngày chạy | Tỷ lệ qua (%) | Citation Accuracy (%) | Ghi chú lỗi |
  |---|---|---|---|---|
  | Lượt 1 (Hiện tại) | 18/09/2026 | 25% (5/20) | 35% | 15 case chưa đạt: câu trả lời chưa khớp kỳ vọng, citation chưa bám sát nguồn truy hồi, lỗi bộ lọc metadata ngày (truyền `--day D01` vẫn bốc nhầm tài liệu Foundation/T06). |
  | Lượt 2 (Mục tiêu CP4/CP5) | 18/09/2026 | ≥ 80% (16/20) | 100% | Fix bộ lọc metadata ngày của retriever; siết prompt ép strict citation; tích hợp template offline cho kịch bản mơ hồ và validate evidence_id cho mindmap. |

<!-- # [GIẢI THÍCH §8]: 
# - Phân công: Ghi rõ tên thành viên tương ứng với từng mảng.
# - Willing users: Điền tên và MSSV của 2 bạn cam kết test thử lúc demo.
# - Multi-prototype: Nhóm đã thử 2 phương án UI nào và vì sao chọn phương án này?
-->
## §8. Phân công & kế hoạch
- Phân công có tên:
  - Lưu Quang Khải (Đội trưởng): Quản trị repository, phát triển RAG.
  - Tô Anh Đức: Đề xuất, phát triển tính năng Ambiguity Disambiguation, Grounded Abstention.
  - Nguyễn Thị Hạ: Đề xuất, phát triển tính năng mindmap
  - Phạm Hương Giang: Đề xuất,  tính năng 
- Willing users:
  1. Lê Thanh Tình — [Điền MSSV] (Học viên phòng E403)
  2. Nguyễn Tiến Lượng — [Điền MSSV] (Học viên phòng E403)
  - Kế hoạch validation: Cho 2 bạn dùng thử trực tiếp prototype để tra cứu chéo Day và thử tính năng click node Mindmap highlight trang slide PDF; đo thời gian tìm ra tài liệu và mức độ hữu ích của gợi ý concept gần nhất.
- Multi-prototype:
  - Phương án A: Chatbot dạng Drawer tích hợp bên phải màn hình danh sách khóa học kèm panel mở rộng hiển thị Mindmap và PDF viewer.
  - Phương án B: Trang tra cứu riêng biệt (`/global-tutor`).
  - Lựa chọn: Chọn Phương án A để giữ luồng học liền mạch (in-workflow), không bắt học viên rời khỏi giao diện chính.

<!-- # [GIẢI THÍCH §9]: 
# - Nhật ký thay đổi: Ghi lại các mốc thời gian nhóm đưa ra các quyết định kỹ thuật quan trọng.
-->
## §9. Changelog
| Thời điểm | Đổi gì | Vì sao (trỏ về feedback/case nào) |
|---|---|---|
| 18/09 - 10:00 | Bỏ sơ đồ mindmap tĩnh, phát triển Dynamic Mindmap (2 luồng: theo bài và theo chủ đề) | Khảo sát cho thấy học viên cần sơ đồ gắn chặt với bài học và chủ đề tra cứu, có khả năng click để highlight vị trí trên PDF. |
| 18/09 - 14:00 | Thêm tiêu chí đánh giá Citation Accuracy vào Quality bar | 64% học viên khảo sát phản ánh bot VLearn cũ thường xuyên trích dẫn sai số trang hoặc link bài. |
| 18/09 - 17:30 | Ghi nhận lỗi Metadata Filter và kết quả benchmark 5/20 vào §5 và §7 | Chạy thử Golden Set lượt 1 đạt 25%, phát hiện lỗi truyền `--day D01` nhưng retriever vẫn lấy nguồn từ Foundation/T06. |
| 18/09 - 19:00 | Tích hợp cơ chế Abstention gợi ý gần nhất & Ambiguity Disambiguation vào §4, §5, §6 | Tránh câu trả lời từ chối cụt ngủn và loại bỏ việc LLM đoán mò câu hỏi mơ hồ, tối ưu chi phí gọi AI theo Mining v2 (7 case uncertain). |
| 18/09 - 20:00 | Hoàn thiện kiến trúc Hybrid Search (BM25 + Dense E5 + RRF) và cơ chế Fallback | Đảm bảo tính tin cậy (reliability) cao, không phụ thuộc hoàn toàn vào LLM khi gặp sự cố mạng hoặc lỗi JSON. |