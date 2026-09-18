"""Shared HTTP request and response contracts."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator


class AskRequest(BaseModel):
    question: Annotated[str, Field(min_length=1, max_length=4000)]

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Vui lòng nhập câu hỏi.")
        return value


class Citation(BaseModel):
    evidence_id: str
    filename: str
    page_number: int = Field(ge=1)
    quote: str
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)
    viewer_url: str = ""
    slide_id: str | None = None
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
