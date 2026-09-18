"""FastAPI integration using the frozen RetrievalService and QAService interfaces."""

import logging
import os
from collections import defaultdict
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.schemas import AskRequest, DayCatalog, DayDetail, DaySlidesPage, QAResponse
from app.ingestion.metadata import normalize_day_id
from app.runtime import bounded_lock, configured_timeout, configure_windows_runtime, request_deadline
from app.viewer.evidence import normalized_bbox, resolve_pdf, viewer_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]
configure_windows_runtime()
load_dotenv(PROJECT_ROOT / ".env")
STATIC_DIR = PROJECT_ROOT / "app" / "viewer" / "static"
log = logging.getLogger(__name__)
app = FastAPI(title="Lecture QA", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
_service_lock = Lock()


def get_services():
    # Delayed imports let the UI and health endpoint work during parallel development.
    with bounded_lock(_service_lock):
        retrieval = getattr(app.state, "retrieval_service", None)
        qa = getattr(app.state, "qa_service", None)
        try:
            if retrieval is None:
                from app.retrieval.service import RetrievalService
                retrieval = RetrievalService()
                app.state.retrieval_service = retrieval
            if qa is None:
                from app.qa.service import QAService
                qa = QAService()
                app.state.qa_service = qa
        except (ImportError, FileNotFoundError) as exc:
            log.warning("Services unavailable: %s", exc)
            raise HTTPException(503, "Chưa sẵn sàng: kiểm tra các module và chạy python scripts/ingest.py.") from exc
    return retrieval, qa


def pdf_root() -> Path:
    configured = Path(os.getenv("PDF_DIR", "data/pdf"))
    return configured if configured.is_absolute() else PROJECT_ROOT / configured


def find_pdf(filename: str) -> Path:
    try:
        return resolve_pdf(pdf_root(), filename)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, "Không tìm thấy tài liệu PDF.") from exc


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/days", response_model=DayCatalog)
def learning_days():
    with request_deadline(5):
        try:
            retrieval, _ = get_services()
            return retrieval.list_days()
        except TimeoutError as exc:
            raise HTTPException(503, "Hệ thống đang xử lý câu hỏi; vui lòng thử lại sau.") from exc


def require_day(day_id):
    try:
        canonical = normalize_day_id(day_id)
    except ValueError as exc:
        raise HTTPException(422, "Ngày học không hợp lệ; dùng Day01 hoặc D01.") from exc
    with request_deadline(5):
        try:
            retrieval, _ = get_services()
            return retrieval, retrieval.get_day(canonical)
        except KeyError as exc:
            raise HTTPException(404, "Không tìm thấy ngày học trong chỉ mục.") from exc
        except TimeoutError as exc:
            raise HTTPException(503, "Hệ thống đang xử lý câu hỏi; vui lòng thử lại sau.") from exc


@app.get("/api/days/{day_id}", response_model=DayDetail)
def learning_day(day_id: str):
    _, day = require_day(day_id)
    return day


@app.get("/api/days/{day_id}/slides", response_model=DaySlidesPage)
def learning_day_slides(day_id: str, offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=200)):
    retrieval, day = require_day(day_id)
    with request_deadline(5):
        try:
            return retrieval.get_day_slides(day["day_id"], offset=offset, limit=limit)
        except TimeoutError as exc:
            raise HTTPException(503, "Hệ thống đang xử lý câu hỏi; vui lòng thử lại sau.") from exc


@app.post("/api/ask", response_model=QAResponse)
def ask(request: AskRequest):
    with request_deadline(configured_timeout("REQUEST_TIMEOUT_SECONDS", 45)):
        return process_ask(request)


def process_ask(request):
    try:
        retrieval, qa = get_services()
        top_k = max(1, min(20, int(os.getenv("TOP_K", "5"))))
        if request.day_id is not None:
            require_day(request.day_id)
            retrieved = retrieval.retrieve(question=request.question, top_k=top_k, day_id=request.day_id)
        else:
            retrieved = retrieval.retrieve(question=request.question, top_k=top_k)
        result = qa.answer(question=request.question, evidence=retrieved.get("evidence", []))
        # Validate the contract and always create local, correctly encoded source links.
        payload = dict(result)
        if isinstance(retrieved.get("debug"), dict):
            payload["debug"] = retrieved["debug"]
        # QA can renumber evidence IDs: match sources by their actual content.
        sources = defaultdict(list)
        for item in retrieved.get("evidence", []):
            if isinstance(item, dict):
                key = (item.get("filename"), item.get("page_number"), item.get("quote", item.get("text")))
                sources[key].append(item)
        slides = {
            item.get("slide_id"): item
            for key in ("slides", "primary_slides", "context_slides")
            for item in retrieved.get(key, []) if isinstance(item, dict)
        }
        payload["citations"] = []
        for citation in result.get("citations", []):
            item = dict(citation)
            matches = sources.get((item.get("filename"), item.get("page_number"), item.get("quote")), [])
            for key in ("slide_id", "block_id"):
                if item.get(key) is not None:
                    matches = [source for source in matches if source.get(key) == item[key]]
            source = matches[0] if len(matches) == 1 else {}
            for key in ("slide_id", "block_id", "document_id", "day_id", "day_number", "day_label", "source_role", "block_score", "evidence_type"):
                if key in source:
                    item[key] = source[key]
            visual = slides.get(item.get("slide_id"), {}).get("visual_analysis")
            if isinstance(visual, dict):
                item["vision_used"] = visual.get("status") == "success"
            payload["citations"].append(item)
        response = QAResponse.model_validate(payload)
        for citation in response.citations:
            citation.bbox = normalized_bbox(citation.bbox)
            citation.viewer_url = viewer_url(citation.model_dump())
        return response
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(503, "Chưa có chỉ mục PDF. Hãy chạy python scripts/ingest.py.") from exc
    except TimeoutError as exc:
        raise HTTPException(503, "Hệ thống đang bận hoặc quá thời gian xử lý; vui lòng thử lại.") from exc
    except Exception as exc:
        log.exception("Question processing failed")
        raise HTTPException(500, "Không xử lý được câu hỏi. Kiểm tra log máy chủ và cấu hình chỉ mục.") from exc


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/viewer")
def viewer(file: str, page: int = Query(ge=1)):
    find_pdf(file)
    return FileResponse(STATIC_DIR / "viewer.html")


@app.get("/pdf/{filename:path}")
def pdf(filename: str):
    path = find_pdf(filename)
    return FileResponse(path, media_type="application/pdf", filename=path.name, content_disposition_type="inline")


@app.get("/api/page")
def page_image(file: str, page: int = Query(ge=1)):
    path = find_pdf(file)
    try:
        import pymupdf as fitz
        with fitz.open(path) as document:
            if page > len(document):
                raise HTTPException(404, "Trang nằm ngoài tài liệu.")
            slide = document[page - 1]
            scale = min(2.0, 1800 / max(slide.rect.width, slide.rect.height))
            image = slide.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            return Response(image.tobytes("png"), media_type="image/png")
    except HTTPException:
        raise
    except ImportError as exc:
        raise HTTPException(503, "Cài pymupdf để xem ảnh trang; có thể mở PDF gốc.") from exc
    except Exception as exc:
        log.exception("PDF rendering failed")
        raise HTTPException(422, "Không đọc được trang PDF này.") from exc
