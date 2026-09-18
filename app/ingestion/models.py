"""JSON-compatible contracts shared with retrieval and the viewer."""

from typing import TypedDict


class LearningDay(TypedDict):
    day_id: str | None
    day_number: int | None
    day_label: str | None


class Document(LearningDay):
    document_id: str
    filename: str
    title: str
    path: str
    total_pages: int


class TextBlock(TypedDict):
    block_id: str
    text: str
    bbox: list[float]


class _NativeSlideRecord(LearningDay):
    slide_id: str
    document_id: str
    document_title: str
    document_total_pages: int
    filename: str
    page_index: int
    page_number: int
    text: str
    blocks: list[TextBlock]
    page_width: float
    page_height: float


class SlideRecord(_NativeSlideRecord, total=False):
    visual_analysis: dict
    retrieval_text: str
