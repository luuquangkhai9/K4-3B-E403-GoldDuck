"""Shared HTTP request and response contracts."""

from typing import Annotated

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


class QAResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
