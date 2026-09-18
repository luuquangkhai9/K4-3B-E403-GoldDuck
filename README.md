# Hỏi đáp bài giảng PDF

Demo FastAPI cho câu hỏi tiếng Việt/Anh, câu trả lời dựa trên bằng chứng và liên kết tới đúng slide. Trình xem dùng PyMuPDF để hiển thị trang và tô vùng bbox; không cần PDF.js hay CDN.

## Chạy demo

Yêu cầu Python 3.10 trở lên. Chạy tại thư mục dự án:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Đặt PDF vào `data/pdf/`, sau đó:

```powershell
python scripts/ingest.py
python scripts/run_demo.py
```

Mở <http://127.0.0.1:8000>, nhập câu hỏi và bấm **Hỏi**. Mỗi nguồn hiển thị ID, tên PDF, số trang và nguyên văn bằng chứng. **Mở nguồn bằng chứng** mở đúng trang và tô bbox nếu có. **Mở PDF gốc** dùng trình xem PDF của trình duyệt với `#page=N`.

Cũng có thể chạy `uvicorn app.api.main:app --reload` tại thư mục dự án. `HOST` và `PORT` cấu hình địa chỉ máy chủ; mặc định `127.0.0.1:8000`.

## Cấu hình

Điền `OPENAI_API_KEY` và `LLM_MODEL` trong `.env` để dùng LLM. Không có key, QA dùng câu trả lời trích xuất theo hợp đồng của Agent3. Đặt `DENSE_ENABLED=false` để dùng lexical retrieval khi không tải được mô hình multilingual E5 hoặc muốn khởi động nhanh. Dense retrieval chạy CPU và lần đầu có thể cần mạng để tải mô hình.

`PDF_DIR`, `INDEX_DIR` mặc định lần lượt là `data/pdf`, `data/index`. `TOP_K` mặc định 5. Nếu đổi đường dẫn trong `.env`, truyền cùng đường dẫn cho ingestion bằng `python scripts/ingest.py --pdf-dir <thư_mục_pdf> --index-dir <thư_mục_index>`; script ingestion hiện đọc biến môi trường của shell, không tự nạp `.env`. Sau khi thêm hoặc sửa PDF, chạy lại ingestion; retrieval tự nạp lại chỉ mục khi có thay đổi.

## API

- `GET /api/health`: `{"status":"ok"}`; xác nhận HTTP server đang chạy, không xác nhận chỉ mục đã sẵn sàng.
- `POST /api/ask`: nhận `{"question":"Gradient descent là gì?"}`, trả `answer` và `citations` theo `HACKATHON_PLAN.md`.
- `GET /viewer?file=lecture.pdf&page=7`: trình xem trang; liên kết citation tự mang bbox để không nhầm ID E1 giữa các câu hỏi.
- `GET /pdf/{filename}`: PDF gốc.
- `GET /api/page?file=lecture.pdf&page=7`: ảnh PNG của trang, số trang bắt đầu từ 1.
- `/docs`: tài liệu API tương tác.

Retrieval và QA được tích hợp qua `RetrievalService().retrieve(question, top_k)` và `QAService().answer(question, evidence)`. Khi module hoặc chỉ mục chưa có, giao diện vẫn mở được và API trả lỗi dễ đọc. Agent4 chỉ sở hữu API/viewer, tài liệu, cấu hình dependencies và script khởi động; ingestion/retrieval/QA do các agent khác cung cấp.

## Kiểm tra

```powershell
python -m pip install httpx
python -m unittest app.api.test_integration -v
```

Kiểm tra tích hợp chạy ingestion, lexical retrieval và extractive QA thật trên PDF tạm có 5 trang đáp án đã biết. Kiểm tra câu hỏi tiếng Việt, nguyên văn bằng chứng, số trang, ảnh trang xoay, bbox và chặn đường dẫn ngoài thư mục PDF. Để kiểm chứng chất lượng trên bài giảng thực tế, ingest PDF thật, hỏi ít nhất 5 câu có trang đáp án đã biết, rồi mở từng citation đối chiếu nội dung slide. PDF scan không có native text cần OCR từ module ingestion; demo cơ bản không tự thêm OCR.
