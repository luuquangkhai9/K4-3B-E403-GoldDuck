"""Shared HTTP request and response contracts."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator


def _clean_scope(value: list[str] | None) -> list[str] | None:
    from app.ingestion.metadata import normalize_scope
    return normalize_scope(value)


class AskRequest(BaseModel):
    question: Annotated[str, Field(min_length=1, max_length=4000)]
    day_id: str | None = None
    scope: list[str] | None = Field(default=None, max_length=50)

    @field_validator("day_id", mode="before")
    @classmethod
    def validate_day(cls, value):
        from app.ingestion.metadata import normalize_day_id
        return normalize_day_id(value) if value is not None else None

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Vui lòng nhập câu hỏi.")
        return value

    @field_validator("scope")
    @classmethod
    def clean_scope(cls, value: list[str] | None) -> list[str] | None:
        return _clean_scope(value)


class MindmapRequest(BaseModel):
    topic: Annotated[str, Field(min_length=1, max_length=200)]
    day_id: str | None = None
    scope: list[str] | None = Field(default=None, max_length=50)

    @field_validator("day_id", mode="before")
    @classmethod
    def validate_day(cls, value):
        from app.ingestion.metadata import normalize_day_id
        return normalize_day_id(value) if value is not None else None

    @field_validator("topic")
    @classmethod
    def strip_topic(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Vui lòng nhập chủ đề sơ đồ tư duy.")
        return value

    @field_validator("scope")
    @classmethod
    def clean_scope(cls, value: list[str] | None) -> list[str] | None:
        return _clean_scope(value)


class MindmapIntentRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=4000)]

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Vui lòng nhập nội dung.")
        return value


class MindmapOverviewRequest(BaseModel):
    scope: list[str] = Field(min_length=1, max_length=50)

    @field_validator("scope")
    @classmethod
    def clean_scope(cls, value):
        return _clean_scope(value)


class Citation(BaseModel):
    evidence_id: str
    filename: str
    page_number: int = Field(ge=1)
    quote: str
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)
    viewer_url: str = ""
    slide_id: str | None = None
    document_id: str | None = None
    day_id: str | None = None
    day_number: int | None = Field(default=None, ge=1)
    day_label: str | None = None
    block_id: str | None = None
    source_role: Literal["primary", "neighbor"] = "primary"
    block_score: float | None = None
    vision_used: bool | None = None
    evidence_type: Literal["native", "visual"] = "native"

    @field_validator("bbox", mode="before")
    @classmethod
    def validate_bbox(cls, value):
        from app.viewer.evidence import normalized_bbox
        return normalized_bbox(value)


class QAResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    grounding: dict[str, Any] | None = None
    debug: dict[str, Any] | None = None


class ChatContext(BaseModel):
    task: Literal["answer", "study_materials", "topic_map", "day_summary"]
    topic: str | None = Field(default=None, max_length=200)
    document_ids: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(default_factory=list, max_length=12)


class ChatRequest(AskRequest):
    context: ChatContext | None = None


class StudyDocument(BaseModel):
    document_id: str
    filename: str
    title: str
    day_id: str | None
    day_number: int | None = None
    day_label: str | None
    total_pages: int = Field(ge=1)
    reason: str
    role: Literal["core", "supporting", "candidate"]
    pages: list[int]
    sources: list[Citation]


class ChatResponse(QAResponse):
    task: Literal["answer", "study_materials", "topic_map", "day_summary"]
    output_format: Literal["text", "mindmap"]
    status: Literal["completed", "partial", "no_evidence", "needs_clarification",
                    "retrieval_timeout", "model_unavailable", "invalid_output"]
    title: str
    branches: list[dict[str, Any]] = Field(default_factory=list)
    documents: list[StudyDocument] = Field(default_factory=list)
    context: ChatContext


class DayDocument(BaseModel):
    document_id: str
    filename: str
    title: str
    day_id: str | None
    day_number: int | None = Field(ge=1)
    day_label: str | None
    total_pages: int = Field(ge=1)
    indexed_slides: int = Field(ge=1)
    searchable_slides: int = Field(ge=0)


class DayDetail(BaseModel):
    day_id: str
    day_number: int = Field(ge=1)
    day_label: str
    document_count: int = Field(ge=1)
    slide_count: int = Field(ge=1)
    searchable_slide_count: int = Field(ge=0)
    documents: list[DayDocument]


class DayCatalog(BaseModel):
    days: list[DayDetail]
    unassigned_documents: list[DayDocument]
    unassigned_document_count: int = Field(ge=0)
    unassigned_slide_count: int = Field(ge=0)


class DaySlidesPage(BaseModel):
    day_id: str
    day_number: int = Field(ge=1)
    day_label: str
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    slides: list[dict[str, Any]]
