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

from app.api.schemas import AskRequest, ChatRequest, ChatResponse, DayCatalog, DayDetail, DaySlidesPage, MindmapIntentRequest, MindmapOverviewRequest, MindmapRequest, QAResponse
from app.ingestion.metadata import normalize_day_id, resolve_day_scope
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


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    with request_deadline(configured_timeout("REQUEST_TIMEOUT_SECONDS", 45)):
        try:
            from app.agent.service import ChatAgent
            from app.qa.intent import extract_explicit_day_scope
            from app.qa.policy import QueryPolicy
            from app.retrieval.query import is_document_discovery
            require_filters(request.day_id, request.scope)
            retrieval, qa = get_services()
            scope = resolve_day_scope(request.day_id, request.scope)
            explicit = extract_explicit_day_scope(request.question)
            if explicit:
                require_filters(scope=explicit)
                if scope and any(day not in scope for day in explicit):
                    raise ValueError("Ngày yêu cầu không nằm trong phạm vi đã chọn.")
            policy = QueryPolicy(retrieval)
            context = request.context.model_dump() if request.context else None
            clarification = policy.clarification(request.question, scope=explicit or scope,
                                                context=context, selected_topic=request.clarification_topic)
            if clarification:
                import re
                mindmap = bool(re.search(r"mindmap|sơ đồ tư duy|so do tu duy", request.question, re.I))
                task = "study_materials" if is_document_discovery(request.question) else "topic_map" if mindmap else "answer"
                return ChatResponse(answer=clarification["question"], status="needs_clarification",
                                    task=task, output_format="mindmap" if mindmap else "text",
                                    title="Làm rõ chủ đề", clarification=clarification,
                                    context=context or {"task": task, "topic": None},
                                    debug={"policy": {"offline": True, "provider_calls": 0}})
            result = ChatAgent(retrieval, qa).run(
                request.question, scope=scope,
                context=context, clarification_topic=request.clarification_topic,
                validate_scope=lambda days: require_filters(scope=days),
                answer_handler=lambda question, days: process_ask(AskRequest(question=question, scope=days)),
            )
            if result["status"] == "no_evidence":
                days = result["debug"]["agent"]["scope_filter"]
                result["suggestions"] = policy.abstention(request.question, scope=days)["suggestions"]
            return ChatResponse.model_validate(result)
        except HTTPException:
            raise
        except ValueError as exc:
            raise HTTPException(422, "Yêu cầu hoặc phạm vi không hợp lệ: " + str(exc)) from exc
        except TimeoutError as exc:
            raise HTTPException(503, "Hệ thống đang bận hoặc quá thời gian xử lý; vui lòng thử lại.") from exc
        except Exception as exc:
            log.warning("Chat orchestration failed (%s)", type(exc).__name__)
            raise HTTPException(500, "Không xử lý được yêu cầu. Kiểm tra log máy chủ và cấu hình chỉ mục.") from exc


def process_ask(request):
    try:
        retrieval, qa = get_services()
        top_k = max(1, min(20, int(os.getenv("TOP_K", "5"))))
        filters = require_filters(request.day_id, request.scope)
        from app.qa.policy import QueryPolicy, question_topic
        scope = resolve_day_scope(request.day_id, request.scope)
        policy = QueryPolicy(retrieval)
        clarification = policy.clarification(request.question, scope=scope, selected_topic=request.clarification_topic)
        if clarification:
            return QAResponse(answer=clarification["question"], status="needs_clarification",
                              clarification=clarification, debug={"policy": {"offline": True, "provider_calls": 0}})
        topic = request.clarification_topic or question_topic(request.question)
        if topic:
            normalized = retrieval.normalize_topic(topic)["topic"]
            if retrieval.topic_supported(normalized, scope=scope) is False:
                return QAResponse(**policy.abstention(request.question, scope=scope),
                                  debug={"policy": {"offline": True, "provider_calls": 0}})
        question = request.question
        if request.clarification_topic:
            question += "\nChủ đề người dùng làm rõ: " + request.clarification_topic
        retrieved = retrieval.retrieve(question=question, top_k=top_k, **filters)
        if not retrieved.get("evidence"):
            return QAResponse(**policy.abstention(question, scope=scope), debug=retrieved.get("debug"))
        result = qa.answer(question=question, evidence=retrieved.get("evidence", []))
        if not result.get("citations"):
            return QAResponse(**policy.abstention(question, scope=scope), debug=retrieved.get("debug"))
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


def require_filters(day_id=None, scope=None):
    try:
        resolve_day_scope(day_id, scope)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    for day in dict.fromkeys((scope or []) + ([day_id] if day_id is not None else [])):
        require_day(day)
    filters = {}
    if day_id is not None:
        filters["day_id"] = day_id
    if scope:
        filters["scope"] = scope
    return filters


def run_mindmap(operation, *, seconds=None):
    with request_deadline(seconds if seconds is not None else configured_timeout("REQUEST_TIMEOUT_SECONDS", 45)):
        try:
            return operation()
        except HTTPException:
            raise
        except FileNotFoundError as exc:
            raise HTTPException(503, "Chưa có chỉ mục PDF. Hãy chạy python scripts/ingest.py.") from exc
        except TimeoutError as exc:
            raise HTTPException(503, "Hệ thống đang bận hoặc quá thời gian tạo sơ đồ; vui lòng thử lại.") from exc
        except Exception as exc:
            log.warning("Mindmap operation failed (%s)", type(exc).__name__)
            raise HTTPException(500, "Không tạo được sơ đồ tư duy. Kiểm tra log máy chủ và cấu hình chỉ mục.") from exc


@app.get("/api/mindmap")
def mindmap(day: str):
    def generate():
        retrieval, metadata = require_day(day)
        _, qa = get_services()
        canonical = metadata["day_id"]
        nodes = retrieval.mindmap_nodes(canonical)
        organized = qa.organize_mindmap(metadata["day_label"], nodes) if nodes else None
        return {"day": canonical, "branches": organized} if organized else retrieval.mindmap(canonical)
    return run_mindmap(generate)


@app.post("/api/mindmap/intent")
def mindmap_intent(request: MindmapIntentRequest):
    def extract():
        retrieval, qa = get_services()
        try:
            intent = qa.extract_mindmap_intent(request.message, retrieval.available_scopes)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return intent or {"day": None, "topic": None}
    return run_mindmap(extract, seconds=8)


@app.post("/api/mindmap/overview")
def overview_mindmap(request: MindmapOverviewRequest):
    def generate():
        retrieval, qa = get_services()
        require_filters(scope=request.scope)
        days = [(day, retrieval.mindmap_nodes(day)) for day in request.scope]
        return qa.overview_mindmap(days)
    return run_mindmap(generate)


@app.post("/api/mindmap/generate")
def generate_mindmap(request: MindmapRequest):
    def generate():
        retrieval, qa = get_services()
        filters = require_filters(request.day_id, request.scope)
        top_k = max(1, min(20, int(os.getenv("TOP_K", "5"))))
        retrieved = retrieval.retrieve(question=request.topic, top_k=top_k, **filters)
        return qa.mindmap(topic=request.topic, evidence=retrieved.get("evidence", []))
    return run_mindmap(generate)


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
