# Đề xuất resolve merge nguyenha59 vào quangkhai

## Kết quả thực hiện

### Bổ sung: lỗi mindmap khoảng ngày trong ảnh

Đã sửa yêu cầu `tao mindmap từ day 1 đến day 3`: parser backend và parser giao diện nhận khoảng/danh sách ngày, không coi phần nối ngày là topic. API `/api/mindmap/overview` tạo sơ đồ tổng quan với nhánh nguồn riêng cho từng ngày. Đầu vào model được lấy cân bằng giữa các ngày; ngày model bỏ sót được bổ sung bằng slide thật. Yêu cầu có topic dùng đúng scope nhiều ngày; khoảng sai không chuyển thành tìm toàn kho.

Kiểm chứng sau bổ sung: **137 test Python và 12 kiểm tra UI qua**. Chạy đúng câu trong ảnh trên Chrome với server/model/corpus thật (không phát lại response): **3 nhánh Day01–Day03, 6 node mỗi nhánh**, hoàn tất khoảng **15 giây** kể cả mở PDF của cả ba ngày; metadata nguồn khớp index và không có lỗi JavaScript. Báo cáo/ảnh ở `data/verification/day_range_report.json` và `day_range_mindmap.png`. Demo đã nạp lại tại port 8000; phiên bản URL JS được đổi để tránh dùng cache cũ.

Đã resolve cả 9 tệp conflict và sửa các lỗi tích hợp nêu trong báo cáo. Lõi RAG được giữ, mindmap/giao diện đã được tích hợp, `day_id` và `scope` dùng cùng metadata ngày học. Mindmap theo ngày và chủ đề không còn bỏ mất chủ đề; gom nhóm tương thích DenseWorker và có fallback lexical khi worker hỏng/quá hạn.

Đã sửa thêm quy tắc tạo mindmap: không dùng tài liệu gần nghĩa để thay thế chủ đề chưa có nguồn; JSON `branches: []` hợp lệ từ model được giữ như một kết quả từ chối, thay vì tạo lại sơ đồ trích xuất. Node giữ nguồn, quote, ngày học và loại bằng chứng từ dữ liệu đã kiểm chứng. UI có timeout, chặn gửi lặp, chụp scope khi gửi, hiển thị Markdown cơ bản bằng DOM an toàn và giữ citation có thể bấm trong phần nhấn mạnh.

Kiểm chứng:

- `python -m unittest discover -q`: **130 test qua**, gồm cả test RAG và mindmap hai nhánh cùng regression tích hợp mới.
- `node scripts/test_ui.cjs`: **8 kiểm tra qua** cho catalog, payload mindmap, ngày không tồn tại, mindmap cả ngày, gửi lặp/scope, phục hồi sau lỗi, AbortController và parser dự phòng.
- `python scripts/verify_live.py`: **5 luồng RAG với model thật đều qua**; Vision/cache, dense CPU, reranker, LLM và V1 compatibility cũng qua.
- Smoke test HTTP trên corpus thật: **13 kiểm tra qua**. Câu hỏi “tranformers” trả lời trong **22,735 giây** ở lần đầu; RAG nhiều ngày **5,828 giây**; mindmap tổng quan Day07 **13,5 giây**; mindmap Embedding trong Day07 **11,922 giây**. Ngày/phạm vi/quote/bbox nguồn được đối chiếu, chủ đề ngoài kho trả nhánh rỗng, unknown day/scope trả 404, bộ lọc mâu thuẫn trả 422.
- Chrome headless: sidebar 10 ngày, gửi lặp, trích dẫn/slide nguồn, mindmap ngày+chủ đề, đường SVG, node/bbox, mindmap sidebar và unknown day đều qua; không có lỗi JavaScript. Kiểm tra thêm nội dung HTML trong Markdown không tạo phần tử ảnh, citation trong chữ đậm vẫn bấm được. Các response model được phát lại từ smoke test thật đã qua; catalog và ảnh PDF được tải từ server thật, tránh gọi model lặp trong kiểm tra giao diện.
- Dữ liệu 2.604 slide / 33 PDF / 10 ngày, 529 Vision success / 2.075 skipped và embedding (2604, 384) vẫn nguyên vẹn, fingerprint/vector hợp lệ.
- Không còn conflict marker hoặc tệp unmerged; kiểm tra cú pháp Python/JS và `git diff --cached --check` qua.

Các tệp đã được stage. **Chưa tạo merge commit hoặc push**; MERGE_HEAD vẫn được giữ để hoàn tất commit theo workflow của người dùng. Demo cũ đã được nạp lại bằng mã đã resolve tại `http://127.0.0.1:8000`; server kiểm chứng tạm đã được dừng.

Báo cáo chi tiết và ảnh kiểm chứng ở `data/verification/live_report.json`, `merge_live_report.json`, `merge_browser_report.json` và `merge_ui_chat.png` (thư mục này được Git ignore). Bản sao các tệp trước resolve nằm trong `data/verification/merge_backup`.

## Trạng thái trước khi resolve

- Nhánh đích: `quangkhai`, HEAD `6c373f6`.
- Merge đang thực hiện: `origin/nguyenha59`, MERGE_HEAD `1c72522`.
- Nhánh local `nguyenha59` ở `fe11792`, thiếu 2 commit so với nhánh remote đang được merge. Phân tích này dùng MERGE_HEAD, không dùng bản local cũ.
- Có **9 tệp conflict, 15 khối conflict**. Không cần chạy lại lệnh merge.
- Khi lập phân tích ban đầu, chưa thay đổi mã nguồn, Git index hoặc hoàn tất merge.
- Python ở từng đầu nhánh riêng lẻ không có lỗi cú pháp khi kiểm tra bằng AST. Working tree trước resolve có lỗi cú pháp trong 7 tệp Python do còn conflict marker.

## Nguyên tắc tích hợp

Giữ pipeline RAG của `quangkhai`: Vision, hybrid retrieval, rerank, neighbor expansion, xếp hạng block, kiểm tra citation, grounded abstention, metadata ngày học và cơ chế chống treo Windows/timeout/DenseWorker. Bổ sung các phương thức mindmap và giao diện của `nguyenha59` trên pipeline đó.

Không chọn toàn bộ `ours` hoặc `theirs` cho các tệp dùng chung. Một số đoạn Git tự merge đã thay đổi tên biến hoặc thêm validator, nên chọn đúng conflict marker vẫn chưa đủ.

## Resolve từng tệp

| Tệp | Đề xuất |
| --- | --- |
| `app/api/main.py` | Giữ API catalog/detail/slides của quangkhai và toàn bộ xử lý `/api/ask`, timeout, metadata citation, bbox/viewer URL. Thêm 3 route mindmap của nguyenha59. Chỉ đăng ký một `/api/days`. Chuẩn hóa và kiểm tra ngày/phạm vi trước retrieval. Route mindmap cũng phải có deadline, bounded lock và phản hồi rõ ràng khi quá hạn. |
| `app/api/schemas.py` | Giữ `day_id`, toàn bộ schema catalog và citation; thêm `scope`, `MindmapRequest`, `MindmapIntentRequest`. Chuẩn hóa scope thành danh sách Day ID, loại trùng; xử lý cả request cũ và mới. |
| `app/ingestion/parser.py` | Giữ suy luận ngày bằng `infer_day_id()` và `day_metadata()`, document title/total pages của quangkhai. Nếu cần `day` để tương thích, lấy từ `learning_day['day_id']`; không tự suy luận lần nữa bằng thư mục đầu tiên của filename. |
| `app/qa/generator.py` | Giữ WMI workaround, `max_retries=0` và `timeout=remaining_timeout(self.timeout)`. Giữ `instructions` tùy chỉnh và truyền `**kwargs` của nguyenha59 trong cùng lời gọi. Temperature mặc định tiếp tục không được gửi; truyền khi cấu hình rõ ràng. |
| `app/qa/service.py` | Giữ nguyên `answer()` của quangkhai, nhất là kiểm tra citation, retry giới hạn, grounding và fallback tìm tài liệu theo ngày. Ghép riêng các phương thức mindmap/organize/intent của nguyenha59 bên ngoài thân `answer()`. Node phải dùng metadata nguồn đã được kiểm chứng. |
| `app/qa/test_service.py` | Giữ cả `import os` và `import json`; giữ hai nhóm test. Fake generator tiếp tục nhận `instructions`. Bổ sung kiểm tra generator vẫn giữ deadline sau khi thêm custom instructions/temperature. |
| `app/retrieval/service.py` | Giữ pipeline và API ngày học của quangkhai; thêm scope nhiều ngày, helpers và các phương thức mindmap. Scope lọc theo `day_id` trước tìm kiếm, không dùng prefix filename sau tìm kiếm toàn corpus. Sửa phần tự merge `by_slide`/`candidates` và tương thích DenseWorker. Chi tiết bên dưới. |
| `app/viewer/static/app.js` | Dùng cấu trúc chat/mindmap/slide panel của nguyenha59. Chuyển helper timeout và thông tin ngày/Vision của quangkhai sang cấu trúc mới. Sửa `loadDays()` để đọc catalog object, chặn gửi lặp, chụp scope tại lúc gửi và luôn phục hồi trạng thái giao diện trong `finally`. |
| `app/viewer/static/index.html` | Dùng layout nguyenha59 cùng CSS đã merge; không giữ đồng thời form cũ và chat mới. Các ID phải khớp JS. Giữ khả năng xem ngày học, trích dẫn và phân biệt bằng chứng Vision trên giao diện mới. |

## Hợp đồng ngày học chung

Nguồn chuẩn là `day_id`/`day_number`/`day_label` của quangkhai. `scope` là danh sách `day_id`, không phải đường dẫn thư mục. `day` chỉ là alias tương thích nếu còn consumer cần dùng.

Đề xuất chữ ký:

```python
def retrieve(self, question, top_k=5, *, day_id=None, scope=None):
    ...
```

Quy tắc:

1. Không truyền bộ lọc, hoặc `scope=[]`: tìm trên toàn bộ corpus.
2. Truyền `day_id`: giữ hành vi lọc một ngày của API hiện có.
3. Truyền `scope`: chuẩn hóa từng giá trị bằng `normalize_day_id()`, loại trùng, lọc nhiều ngày.
4. Truyền cả hai: dùng giao của hai bộ lọc; nếu giao rỗng, trả 422. Không âm thầm bỏ một bộ lọc.
5. Bộ lọc sai định dạng: 422. Day ID hợp lệ nhưng không có trong catalog: 404 ở API. Không chuyển thành tìm toàn corpus.
6. Retrieval trực tiếp với ngày không tồn tại vẫn giữ kết quả rỗng như hành vi hiện tại.

Tạo `allowed_indices` từ metadata slide đã chuẩn hóa. BM25 chạy trên tập được phép rồi ánh xạ chỉ số về corpus; dense nhận `allowed_indices`. Neighbor expansion cũng phải nằm trong scope. Áp dụng chung cho hỏi đáp và mindmap theo chủ đề.

`GET /api/days` giữ response hiện tại của quangkhai:

```json
{
  "days": [{"day_id": "Day01", "day_label": "Day 01", "document_count": 3}],
  "unassigned_documents": [],
  "unassigned_document_count": 0,
  "unassigned_slide_count": 0
}
```

Đây là minh họa rút gọn; mỗi phần tử vẫn phải có các trường còn lại mà `DayDetail` yêu cầu. JS dùng `catalog.days.map(day => day.day_id)` cho danh sách ID, dùng object gốc để hiển thị nhãn/số tài liệu. Không đổi catalog thành `['Day01', ...]`, vì sẽ phá các API/test ngày học hiện có.

## Lỗi tích hợp ngoài conflict marker

### 1. `_evidence()` bị trộn hai thuật toán

Working tree hiện tại khởi tạo `by_slide`, trong khi đoạn quangkhai dùng `candidates.append(...)`. Chọn các khối HEAD sẽ để lại `NameError`. Chọn các khối nguyenha59 lại để thân hàm dùng `rank_blocks` và `block_score` không phù hợp chữ ký/selection của nhánh đó.

Resolve từ **toàn bộ `_evidence()` của quangkhai**, bảo đảm `candidates = []` được khởi tạo và `block_score` đến từ tuple đã xếp hạng. Sau đó bổ sung `_is_usable_evidence_text()` để lọc footer, icon thuần trang trí; giữ nguyên quote gốc, Vision evidence, continuation merging, xếp hạng E5 và giới hạn evidence cấu hình.

Thuật toán lấy tối đa 12 block và ưu tiên 7 block đầu slide của nguyenha59 thay đổi hành vi RAG. Không thay pipeline bằng thuật toán này trong merge tính năng mindmap; nếu muốn áp dụng, cần đánh giá chất lượng riêng.

### 2. Gom nhóm mindmap không tương thích DenseWorker

`_group_into_branches()` đọc `dense.slides`, nhưng DenseWorker mặc định của quangkhai không có thuộc tính này. Khi có agenda và dense được bật, đường fallback này có thể lỗi `AttributeError`.

Đề xuất truyền danh sách slide/chỉ số nguồn một cách rõ ràng vào helper, dùng các chỉ số toàn corpus mà dense search trả về để ánh xạ node. Dense search chỉ xét ngày được chọn, có deadline và không khởi tạo model trong tiến trình HTTP.

Nếu dense lỗi/quá hạn/không có kết quả hữu ích, thực hiện lại nhánh gom nhóm theo token. Hiện tại chỉ kiểm tra dense khác None có thể bỏ qua fallback lexical khi worker đã hỏng. `available_scopes`, `mindmap_nodes`, `mindmap` phải dùng `bounded_lock`, và available scopes lấy từ catalog gồm cả slide không có text.

### 3. Request schema dễ mất scope hoặc lỗi validator

Git đã tự thêm validator `clean_scope` bên ngoài khối conflict. Chỉ giữ HEAD ở khối định nghĩa `AskRequest` sẽ giữ validator cho field không tồn tại, gây lỗi khởi tạo model Pydantic. Nếu chỉ xóa validator rồi giữ `day_id`, client mới gửi scope có thể bị bỏ qua và tìm ngoài phạm vi đã chọn.

Phải giữ cả field `day_id` và `scope`, cùng quy tắc chuẩn hóa chung.

### 4. `answer()` không được ghép nối hai thân hàm

Đoạn phía nguyenha59 trong conflict dùng `generated` nhưng phần tự merge trước đó đã giữ logic HEAD tới `by_id`, không có lời gọi tạo `generated` ở vị trí đó. Chọn toàn bộ đoạn này sẽ vừa mất kiểm soát grounding vừa có biến chưa được tạo.

Giữ thân `answer()` HEAD. Chỉ lấy các phương thức bắt đầu từ `_extractive_mindmap()` trở xuống của phía nguyenha59.

### 5. Hai ý định mindmap phải được phân biệt

JS nguyenha59 ưu tiên mindmap cả ngày khi intent có day hợp lệ, ngay cả khi có topic. Yêu cầu “tạo mindmap Transformer buổi 7” vì thế bỏ mất chủ đề Transformer.

Hành vi đề xuất:

- Chỉ day: mindmap tổng quan ngày đó.
- Chỉ topic: mindmap topic trong scope đã chọn, hoặc toàn corpus nếu không chọn scope.
- Day và topic: mindmap topic trong ngày đã chỉ định, theo quy tắc giao scope nếu có cả bộ lọc sidebar.
- Day không tồn tại: thông báo lỗi ngày, không tạo mindmap toàn corpus hoặc sơ đồ có tiêu đề “Chủ đề”.
- Không đủ evidence: trả nhánh rỗng/thông báo thiếu nguồn; không dùng dense hit yếu để mặc nhiên xác nhận có kiến thức phù hợp. Dùng chính sách kiểm tra evidence nhất quán với RAG khi có threshold cấu hình.

### 6. Giao diện mới phải giữ cơ chế chống treo

Các fetch mới cho `/api/ask`, `/api/days` và các route mindmap chưa có AbortController. Chuyển helper timeout sang UI mới, đồng thời bổ sung deadline ở backend mindmap.

Luồng mindmap chat gồm intent rồi generate; phải có giới hạn cho từng bước và quy tắc ngân sách tổng. Intent quá hạn cần chuyển sang parser dự phòng trong thời gian hữu hạn. Slide image fetch cần helper hỗ trợ blob; không gọi helper luôn parse JSON cho route ảnh.

Chặn `send()` nếu đang xử lý để Enter/click gợi ý không tạo nhiều request dù nút gửi bị disable. Scope sử dụng cho request phải là bản chụp tại lúc gửi, tránh đổi sidebar giữa lúc chờ rồi gắn nhãn nguồn sai.

## Phần Git tự merge và dữ liệu

- `app/qa/prompts.py`: giữ prompt RAG hiện tại và các prompt mindmap mới đã được thêm.
- `app/api/test_integration.py`: giữ test mới cho giao diện/mindmap và các test RAG/ngày học; xóa `import json` bị lặp.
- `app/retrieval/test_retrieval.py`: giữ cả test RAG và test mindmap; cập nhật helper gom nhóm/FakeDense theo giao diện tương thích DenseWorker. Bổ sung test scope nhiều ngày, vì test mindmap với `dense_enabled=False` hoặc FakeDense có `.slides` chưa chứng minh chạy được với worker thật.
- `app/ingestion/models.py`: nếu giữ `day`, định nghĩa nó là alias tương thích với `day_id`, tốt nhất optional để fixture/index cũ không bị buộc phải có trường mới.
- `style.css` và `viewer.html`: giữ giao diện phía nguyenha59, kiểm tra cả viewer riêng và slide panel nhúng.
- So sánh `slides.json` working tree với HEAD: cùng **2.604 slide / 33 PDF / 10 ngày**; **chỉ thêm `day` cho 2.604 slide**, không đổi trường nào khác; tất cả alias hiện tại trùng `day_id`.
- Vision giữ **529 success, 2.075 skipped**. Embedding hiện tại có shape **(2604, 384)**, fingerprint khớp dữ liệu tìm kiếm, tất cả vector hữu hạn và chuẩn hóa hợp lệ. Không cần ingest lại, gọi Vision API hay rebuild embedding chỉ để merge alias ngày học. Tiếp tục kiểm tra fingerprint/shape của embedding sau resolve.

## Kiểm chứng bắt buộc sau resolve

1. Không còn conflict marker; `git diff --name-only --diff-filter=U` rỗng sau khi stage các tệp đã resolve. Python/JS không còn lỗi cú pháp, `git diff --check` qua.
2. Chạy toàn bộ `python -m unittest discover -q`, giữ các regression RAG, metadata Day, Vision, citation/bbox và timeout; chạy test mindmap mới trong cùng bộ kiểm thử.
3. Hỏi trên toàn corpus, một ngày, nhiều ngày; mọi primary/neighbor/evidence phải thuộc phạm vi yêu cầu. API cũ gửi `day_id` vẫn hoạt động.
4. Lặp câu “Tôi muốn học về tranformers, tôi cần học những tài liệu nào nằm ở ngày nào”; xác nhận sửa typo, tài liệu/ngày/trích dẫn và deadline vẫn đúng.
5. Mindmap qua nút sidebar; chat chỉ day, chỉ topic, day+topic; unknown day và thiếu nguồn không chuyển sang scope toàn khóa ngoài ý muốn.
6. Mindmap chạy khi model/LLM thiếu hoặc lỗi, worker treo, JSON LLM sai, ID/index nguồn giả. Giữ fallback có giới hạn thời gian, không nhận nguồn bịa.
7. Test gom nhóm agenda với backend có giao diện giống DenseWorker, không giả định `.slides`; kiểm tra trường hợp dense thất bại vẫn gom nhóm lexical.
8. Click citation và node mindmap mở đúng PDF/trang/bbox; hiển thị ngày và nguồn Vision đúng. Không gửi lặp bằng Enter và không gắn scope khác request.
9. Smoke test model cấu hình thật sau khi unit test qua; kiểm tra log không lộ key. Sau đó mới xác nhận merge hoạt động và hoàn tất commit theo yêu cầu của người dùng.

**Kết luận phân tích ban đầu:** kết hợp lõi RAG quangkhai với mindmap/giao diện nguyenha59, có adapter ngày học và DenseWorker. Kết quả thực hiện và kiểm chứng sau resolve được ghi ở đầu báo cáo.
