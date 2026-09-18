"""FastAPI integration using the frozen RetrievalService and QAService interfaces."""

import logging
import os
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.schemas import AskRequest, MindmapRequest, QAResponse
from app.viewer.evidence import normalized_bbox, resolve_pdf, viewer_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
STATIC_DIR = PROJECT_ROOT / "app" / "viewer" / "static"
log = logging.getLogger(__name__)
app = FastAPI(title="Lecture QA", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
_service_lock = Lock()


def get_services():
    # Delayed imports let the UI and health endpoint work during parallel development.
    with _service_lock:
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


@app.get("/api/days")
def days():
    retrieval, _ = get_services()
    return {"days": retrieval.available_scopes}


@app.get("/api/mindmap")
def mindmap(day: str):
    retrieval, qa = get_services()
    if day not in retrieval.available_scopes:
        raise HTTPException(404, "Không tìm thấy buổi học này.")
    # Let the LLM group the day's real, already-extracted headings into topic
    # branches when available (it only ever picks among them, never invents
    # one) — falls back to the rule-based/embedding grouping otherwise.
    nodes = retrieval.mindmap_nodes(day)
    organized = qa.organize_mindmap(day, nodes) if nodes else None
    return {"day": day, "branches": organized} if organized else retrieval.mindmap(day)


@app.post("/api/mindmap/generate")
def generate_mindmap(request: MindmapRequest):
    try:
        retrieval, qa = get_services()
        top_k = max(1, min(20, int(os.getenv("TOP_K", "5"))))
        retrieved = retrieval.retrieve(question=request.topic, top_k=top_k, scope=request.scope)
        return qa.mindmap(topic=request.topic, evidence=retrieved.get("evidence", []))
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(503, "Chưa có chỉ mục PDF. Hãy chạy python scripts/ingest.py.") from exc
    except Exception as exc:
        log.exception("Mindmap generation failed")
        raise HTTPException(500, "Không tạo được sơ đồ tư duy. Kiểm tra log máy chủ và cấu hình chỉ mục.") from exc


@app.post("/api/ask", response_model=QAResponse)
def ask(request: AskRequest):
    try:
        retrieval, qa = get_services()
        top_k = max(1, min(20, int(os.getenv("TOP_K", "5"))))
        retrieved = retrieval.retrieve(question=request.question, top_k=top_k, scope=request.scope)
        result = qa.answer(question=request.question, evidence=retrieved.get("evidence", []))
        # Validate the contract and always create local, correctly encoded source links.
        response = QAResponse.model_validate(result)
        for citation in response.citations:
            citation.bbox = normalized_bbox(citation.bbox)
            citation.viewer_url = viewer_url(citation.model_dump())
        return response
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(503, "Chưa có chỉ mục PDF. Hãy chạy python scripts/ingest.py.") from exc
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
