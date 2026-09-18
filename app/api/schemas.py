"""Shared HTTP request and response contracts."""

from typing import Annotated

from pydantic import BaseModel, Field, field_validator


def _clean_scope(value: list[str] | None) -> list[str] | None:
    if value is None:
        return None
    cleaned = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return cleaned or None


class AskRequest(BaseModel):
    question: Annotated[str, Field(min_length=1, max_length=4000)]
    scope: list[str] | None = Field(default=None, max_length=50)

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
    scope: list[str] | None = Field(default=None, max_length=50)

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


class Citation(BaseModel):
    evidence_id: str
    filename: str
    page_number: int = Field(ge=1)
    quote: str
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)
    viewer_url: str = ""


class QAResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
