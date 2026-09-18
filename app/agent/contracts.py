"""Validated plans and evidence-only selections; no model-authored paths."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TaskPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task: Literal["answer", "study_materials", "topic_map", "day_summary"]
    output_format: Literal["text", "mindmap"]
    topic: str | None = Field(max_length=200)
    scope: list[str] | None = Field(max_length=50)


class DocumentSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str = Field(min_length=1, max_length=120)
    evidence_ids: list[str] = Field(min_length=1, max_length=6)
    role: Literal["core", "supporting", "mention"]
    reason: str = Field(min_length=1, max_length=500)


class StudyReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    documents: list[DocumentSelection] = Field(max_length=12)
    # One refinement is enough for the MVP; it cannot start an unbounded loop.
    missing_queries: list[str] = Field(max_length=1)
