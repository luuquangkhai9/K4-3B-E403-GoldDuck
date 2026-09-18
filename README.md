# Hỏi đáp bài giảng PDF

Demo FastAPI cho câu hỏi tiếng Việt/Anh, câu trả lời dựa trên bằng chứng và liên kết tới đúng slide. Trình xem dùng PyMuPDF để hiển thị trang và tô vùng bbox; không cần PDF.js hay CDN.

## Chạy demo

Yêu cầu Python 3.10 trở lên. Chạy tại thư mục dự án:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
New-Item -ItemType Directory -Force data/pdf
```

Đặt PDF vào `data/pdf/`, sau đó:

```powershell
python scripts/ingest.py
python scripts/run_demo.py
```

Mở <http://127.0.0.1:8000>, nhập câu hỏi và bấm **Hỏi**. Mỗi nguồn hiển thị ID, tên PDF, số trang và bằng chứng. Nguồn native giữ nguyên văn PDF; nguồn visual được ghi rõ là mô tả hình ảnh do Vision tạo. **Mở nguồn bằng chứng** mở đúng trang và tô bbox nếu có. **Mở PDF gốc** dùng trình xem PDF của trình duyệt với `#page=N`.

Cũng có thể chạy `uvicorn app.api.main:app --reload` tại thư mục dự án. `HOST` và `PORT` cấu hình địa chỉ máy chủ; mặc định `127.0.0.1:8000`.

## Cấu hình

Điền `OPENAI_API_KEY` và `LLM_MODEL` trong `.env` để dùng LLM. Không có key, QA dùng câu trả lời trích xuất từ bằng chứng. Đặt `DENSE_ENABLED=false` để dùng lexical retrieval khi không tải được mô hình multilingual E5 hoặc muốn khởi động nhanh. Dense retrieval chạy CPU và lần đầu có thể cần mạng để tải mô hình.

Trong demo, E5 chạy trong tiến trình riêng với `DENSE_CPU_THREADS=1`. `DENSE_TIMEOUT_SECONDS=15` giới hạn thời gian truy hồi; `DENSE_BLOCK_TIMEOUT_SECONDS=5` giới hạn xếp hạng bằng chứng. Khi E5 lỗi hoặc quá hạn, tiến trình được dừng và dịch vụ tiếp tục bằng BM25; E5 không được thử lại cho đến khi khởi động lại hoặc chỉ mục thay đổi. Nếu cần tải model hoặc tạo embeddings cho kho lớn, chạy trước `python -m app.retrieval --require-dense`; lệnh chuẩn bị này không chịu timeout HTTP.

`REQUEST_TIMEOUT_SECONDS=45` đặt ngân sách chờ khóa, E5 và các API cho một câu hỏi. API danh mục ngày giới hạn chờ khóa ở 5 giây và trả HTTP 503 nếu đang bận. Giao diện giới hạn chờ câu trả lời ở 60 giây và luôn mở lại nút Hỏi sau lỗi. Sau khi sửa mã hoặc cấu hình, dừng demo bằng `Ctrl+C` rồi chạy lại `python scripts/run_demo.py` để áp dụng.

Trên Windows/Python có cơ chế dò WMI, ứng dụng giới hạn bước đọc thông tin nền tảng ở 250 ms. Nếu WMI không đáp ứng, Python dùng thông tin Windows dự phòng; điều này tránh PyTorch và OpenAI SDK bị treo trước khi timeout truy hồi hoặc HTTP có hiệu lực.

`PDF_DIR`, `INDEX_DIR` mặc định lần lượt là `data/pdf`, `data/index`. `TOP_K` mặc định 5. Ingestion và API đều tự nạp `.env` ở thư mục dự án; biến môi trường của shell được ưu tiên hơn `.env`. Có thể ghi đè đường dẫn ingestion bằng `python scripts/ingest.py --pdf-dir <thư_mục_pdf> --index-dir <thư_mục_index>`. Đường dẫn tương đối được tính từ thư mục dự án. Sau khi thêm hoặc sửa PDF, chạy lại ingestion; retrieval tự nạp lại chỉ mục khi có thay đổi. Nếu thư mục PDF không tồn tại hoặc mọi PDF đều lỗi, ingestion báo lỗi và giữ chỉ mục cũ. Thư mục PDF tồn tại nhưng rỗng sẽ tạo chỉ mục rỗng.

## API

- `GET /api/health`: `{"status":"ok"}`; xác nhận HTTP server đang chạy, không xác nhận chỉ mục đã sẵn sàng.
- `POST /api/ask`: nhận `{"question":"Gradient descent là gì?"}`, trả `answer` và `citations` theo `HACKATHON_PLAN.md`.
- `GET /api/days`: danh sách ngày học, các tài liệu của từng ngày, số slide và tài liệu chưa gán ngày.
- `GET /api/days/Day01`: metadata của ngày và danh sách tất cả PDF thuộc ngày đó.
- `GET /api/days/Day01/slides?offset=0&limit=100`: toàn bộ slide của ngày theo thứ tự tên tệp và số trang, có phân trang (tối đa 200 slide mỗi lần).
- `GET /viewer?file=lecture.pdf&page=7`: trình xem trang; liên kết citation tự mang bbox để không nhầm ID E1 giữa các câu hỏi.
- `GET /pdf/{filename}`: PDF gốc.
- `GET /api/page?file=lecture.pdf&page=7`: ảnh PNG của trang, số trang bắt đầu từ 1.
- `/docs`: tài liệu API tương tác.

Retrieval và QA được tích hợp qua `RetrievalService().retrieve(question, top_k)` và `QAService().answer(question, evidence)`. Khi module chưa có, giao diện vẫn mở được và API trả lỗi dễ đọc. Khi chỉ mục chưa có hoặc rỗng, QA trả thông báo không đủ thông tin và danh sách citation rỗng. Nếu chỉ mục mới sai cấu trúc, retrieval giữ dữ liệu hợp lệ đã nạp và thử nạp lại ở yêu cầu tiếp theo.

## Metadata theo ngày học

Mỗi tài liệu và slide có `day_id` (ví dụ `Day01`), `day_number` (`1`) và `day_label` (`Day 01`). Slide còn lưu `document_id`, `document_title` và `document_total_pages` để liên kết với tài liệu. Một ngày có thể chứa nhiều PDF; API danh mục nhóm tất cả các tệp theo ngày, kể cả slide không có nội dung tìm kiếm. Danh mục được tạo từ chính `slides.json` để đồng bộ với chỉ mục đang dùng.

Thư mục ngày gần tệp nhất là nguồn ưu tiên: `data/pdf/Day01/bai-a.pdf` và `data/pdf/Day01/bai-b.pdf` đều thuộc `Day01`. Nếu không có thư mục ngày, ingestion tìm dấu hiệu ngày rõ ràng trong tên tệp, ví dụ `day01-lecture.pdf` hoặc `1-Day 08 Lecture.pdf`. Tệp không xác định được ngày, hoặc tên chứa nhiều ngày khác nhau, có metadata ngày là `null`; chúng được liệt kê trong `unassigned_documents` và vẫn tìm được khi chọn tất cả ngày. `D01`, `day1` và `1` được chuẩn hóa thành `Day01` trong bộ lọc.

Giao diện có bộ chọn ngày học. Có thể lọc trực tiếp bằng `POST /api/ask` với `{"question":"Embedding là gì?","day_id":"Day07"}` hoặc CLI `python -m app.retrieval --day D07 --query "Embedding là gì?"`. Bộ lọc giới hạn tập tài liệu trước khi BM25/dense chọn top-k; reranker, slide lân cận và citation đều giữ đúng phạm vi ngày. Bỏ `day_id` hoặc dùng `null` để tìm trên toàn kho. Ngày sai định dạng trả HTTP 422; ngày chưa có trong chỉ mục trả HTTP 404.

Với câu hỏi tìm tài liệu như “Tôi muốn học về tranformers, tôi cần học những tài liệu nào nằm ở ngày nào”, truy hồi tách chủ đề học, sửa lỗi gõ gần với thuật ngữ có trong kho và chọn bằng chứng từ nhiều PDF. Câu trả lời liệt kê tên tài liệu cùng ngày học và citation; khi LLM lỗi, câu trả lời trích xuất cũng giữ thông tin này. Danh sách được xếp hạng theo liên quan, không bảo đảm liệt kê mọi tài liệu trong kho.

Để chuẩn bị chức năng tổng hợp kiến thức một ngày, dùng `/api/days/{day_id}` lấy đủ danh sách tài liệu, rồi đọc hết các trang `/api/days/{day_id}/slides` đến khi đủ `total`. Các trang bao gồm cả native text, blocks và phân tích Vision. Kết quả `/api/ask` là các bằng chứng được xếp hạng, không bảo đảm bao phủ mọi bài học trong ngày.

Với chỉ mục đã có Vision, bổ sung metadata bằng `python scripts/update_metadata.py`. Lệnh đọc metadata PDF và cập nhật JSON nguyên tử, giữ slide/block ID, text, bbox và kết quả Vision; không gọi Vision hoặc tính lại embeddings. Những lần ingestion sau tự tạo đầy đủ metadata ngày học.

## Tích hợp V2

`/api/ask` giữ `answer`, `citations` và bổ sung `grounding`, `debug` khi dịch vụ cung cấp (nếu không có, giá trị là `null`). Citation bổ sung `slide_id`, `block_id`, `source_role`, `block_score`, `vision_used`, `evidence_type`. API đối chiếu nội dung và ID slide/block để giữ đúng metadata ngay cả khi QA đánh lại ID hoặc các block có cùng nguyên văn; liên kết luôn trỏ tới viewer nội bộ và mang bbox của chính citation.

Phân tích Vision thành công được dùng cho cả truy hồi và bằng chứng QA. Nguồn `evidence_type=visual` chứa mô tả hình ảnh, có bbox rỗng và mở đúng trang PDF để đối chiếu; nguồn `native` chứa nguyên văn trích xuất. Nếu Vision thất bại, ingestion giữ native text. Slide không có native text hoặc retrieval text hữu ích không được đưa vào dense retrieval. Reranker thất bại giữ thứ tự RRF và số lượng kết quả theo `top_k`.

Trước khi xếp hạng block V2, các phần liên tiếp của một câu bị PDF tách block được nối lại khi vị trí và nguyên văn xác nhận chúng là đoạn tiếp nối. Citation giữ ID block đầu và bbox bao cả đoạn; không nối qua cột, bullet mới hoặc footer. Điều này tránh mất một phần danh sách, chẳng hạn từ “prompts” trong câu “MCP server công bố tools, resources, và prompts”.

Các biến V2 nằm trong `.env.example`: Vision (`VISION_ENABLED`, `VISION_PROVIDER`, `VISION_MODEL`, `VISION_TEXT_THRESHOLD`, `VISION_IMAGE_RATIO_THRESHOLD`), reranker (`RERANK_ENABLED`, `RERANK_PROVIDER`, `RERANK_API_KEY`, `RERANK_MODEL`, `RERANK_CANDIDATES`, `RERANK_TOP_K`), ngữ cảnh (`NEIGHBOR_EXPANSION_ENABLED`, `NEIGHBOR_DISTANCE`), bằng chứng (`EVIDENCE_TOP_K`, `MAX_EVIDENCE_PER_SLIDE`) và grounding (`NO_ANSWER_ENABLED`, `NO_ANSWER_THRESHOLD`, `CITATION_VALIDATION_ENABLED`). Điền model và key theo provider; cấu hình model và ngưỡng còn trống cần được xử lý theo mặc định của module sở hữu. Vision chỉ chạy lúc ingestion; sau khi bật Vision cần chạy lại `python scripts/ingest.py`. Không cần GPU hoặc SDK reranker riêng.

`VISION_TIMEOUT` mặc định 30 giây; `RERANK_TIMEOUT_SECONDS` mặc định 10 giây. Vision dùng `OPENAI_API_KEY`, hoặc `VISION_API_KEY` nếu cấu hình riêng. Ngưỡng Vision phải hợp lệ và hữu hạn; cấu hình sai sẽ tắt Vision để bảo toàn ingestion. `NO_ANSWER_THRESHOLD` để trống sẽ tắt kiểm tra ngưỡng điểm; hệ thống vẫn từ chối khi không có bằng chứng hoặc LLM báo không đủ thông tin. Khi đặt ngưỡng, cần hiệu chỉnh theo phương pháp xếp hạng block: cosine E5 và điểm lexical có thang đo khác nhau.

Với kho PDF lớn, chạy `python scripts/ingest.py --vision-workers 4` để giới hạn bốn yêu cầu Vision đồng thời; việc đọc và render PDF vẫn chạy tuần tự. Cache thành công được tái sử dụng. Lệnh báo số slide Vision thành công, bỏ qua và thất bại; nếu có lỗi PDF hoặc Vision, lệnh trả mã lỗi khác 0 nhưng giữ native text cho các trang Vision thất bại. Chạy lại để thử các trang chưa thành công. Lỗi HTTP tạm thời hoặc timeout được thử tối đa ba lần. Chỉ mục được thay thế sau khi mọi yêu cầu đã hoàn tất; dense embeddings sẽ được cập nhật ở lần truy hồi kế tiếp.

Để kiểm tra V1, đặt `VISION_ENABLED=false`, `RERANK_ENABLED=false`, `NEIGHBOR_EXPANSION_ENABLED=false`, `CITATION_VALIDATION_ENABLED=false`, `NO_ANSWER_ENABLED=false`. Để kiểm tra V2, bật lại các biến này và cấu hình provider/model. Lệnh khởi động vẫn là `python scripts/run_demo.py`. Thẻ nguồn hiển thị vai trò chính/lân cận, trạng thái phân tích hình ảnh khi có; phần **Thông tin kiểm tra** hiển thị debug retrieval và grounding.

`python -m unittest app.api.test_integration -v` kiểm tra pipeline V1 thật, nguồn Vision tới QA/viewer, metadata của các block trùng nội dung và toàn bộ pipeline V2 với model/client giả lập. Năm tình huống hợp đồng gồm câu hỏi tiếng Việt, hỏi tiếng Việt về slide tiếng Anh, slide hình ảnh, ngữ cảnh lân cận và câu ngoài kho. Các kiểm thử cô lập cấu hình `.env` để không gọi API trả phí. Chúng xác nhận luồng dữ liệu và fallback, không chứng minh chất lượng mô hình trên bài giảng thực tế. Để kiểm chứng chất lượng, cần chạy năm tình huống trên PDF thật, kiểm tra trang/quote, mở nguồn và xác nhận từ chối trả lời câu ngoài kho.

## Chạy kiểm thử

Kiểm chứng các API/model đã cấu hình bằng smoke test có đáp án biết trước:

```powershell
python scripts/verify_live.py
python scripts/verify_live.py --corpus
```

Các lệnh này gọi API thật và có thể phát sinh phí. Lệnh đầu kiểm tra năm luồng V2, cache Vision và V1 fallback trên PDF mẫu; chỉ một trang hình ảnh chưa cache cần gọi Vision. Lệnh `--corpus` kiểm tra QA trên chỉ mục hiện tại và một slide hình ảnh thật. Báo cáo JSON, PDF mẫu và cache kiểm chứng nằm trong `data/verification/`. Chỉ mục bài giảng gốc không bị thay thế. Có thể chạy riêng một tình huống bằng `--only neighbor` (hoặc `visual`, `no_answer`, `vietnamese_native`, `english_to_vietnamese`).

```powershell
python -m pip install httpx
python -m unittest discover -v
```

Lệnh trên chạy toàn bộ kiểm thử ingestion, retrieval, QA và API. Kiểm tra tích hợp chạy ingestion, lexical retrieval và extractive QA thật trên PDF tạm có 5 trang đáp án đã biết; kiểm tra câu hỏi tiếng Việt, nguyên văn bằng chứng, số trang, ảnh trang xoay, bbox và chặn đường dẫn ngoài thư mục PDF. Các kiểm thử hồi quy kiểm tra bảo toàn chỉ mục, cấu hình `.env`, dữ liệu sai cấu trúc và xếp hạng từ khóa phổ biến. Dense retrieval và LLM được kiểm tra bằng mô hình/client giả lập, không gọi dịch vụ bên ngoài. Để kiểm chứng chất lượng trên bài giảng thực tế, ingest PDF thật, hỏi ít nhất 5 câu có trang đáp án đã biết, rồi mở từng citation đối chiếu nội dung slide. PDF scan không có native text cần OCR; demo cơ bản không tự thêm OCR.
