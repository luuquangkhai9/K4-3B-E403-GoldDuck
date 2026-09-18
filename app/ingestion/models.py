"""JSON-compatible contracts shared with retrieval and the viewer."""

from typing import TypedDict


class Document(TypedDict):
    document_id: str
    filename: str
    title: str
    path: str
    total_pages: int
    day: str | None


class TextBlock(TypedDict):
    block_id: str
    text: str
    bbox: list[float]


class SlideRecord(TypedDict):
    slide_id: str
    document_id: str
    filename: str
    day: str | None
    page_index: int
    page_number: int
    text: str
    blocks: list[TextBlock]
    page_width: float
    page_height: float
