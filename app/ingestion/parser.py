"""Extract native PDF text with bounding boxes in displayed-page coordinates."""

import hashlib
from pathlib import Path

from .models import Document, SlideRecord, TextBlock


def parse_pdf(path: str | Path, *, filename: str | None = None) -> tuple[Document, list[SlideRecord]]:
    try:
        import pymupdf as fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required. Install it with: python -m pip install pymupdf") from exc

    path = Path(path)
    source_name = filename if filename is not None else path.name
    document_id = "doc_" + hashlib.sha256(source_name.encode("utf-8")).hexdigest()[:16]
    slides: list[SlideRecord] = []
    with fitz.open(path) as pdf:
        if pdf.needs_pass:
            raise ValueError(f"Password-protected PDF: {source_name}")
        document: Document = {
            "document_id": document_id,
            "filename": source_name,
            "title": (pdf.metadata or {}).get("title") or path.stem,
            "path": path.as_posix(),
            "total_pages": len(pdf),
        }
        for page_index, page in enumerate(pdf):
            width, height = float(page.rect.width), float(page.rect.height)
            if width <= 0 or height <= 0:
                raise ValueError(f"Invalid page dimensions in {source_name}, page {page_index + 1}")
            slide_id = f"{document_id}_p{page_index + 1:04d}"
            blocks: list[TextBlock] = []
            for raw in page.get_text("blocks", sort=True):
                if raw[6] != 0 or not raw[4].strip():
                    continue
                # PyMuPDF text boxes are unrotated; the viewer displays rotated pages.
                rect = fitz.Rect(raw[:4]) * page.rotation_matrix
                bbox = [
                    max(0.0, min(1.0, rect.x0 / width)),
                    max(0.0, min(1.0, rect.y0 / height)),
                    max(0.0, min(1.0, rect.x1 / width)),
                    max(0.0, min(1.0, rect.y1 / height)),
                ]
                blocks.append({
                    "block_id": f"{slide_id}_b{len(blocks):03d}",
                    "text": raw[4].strip(),
                    "bbox": bbox,
                })
            slides.append({
                "slide_id": slide_id,
                "document_id": document_id,
                "filename": source_name,
                "page_index": page_index,
                "page_number": page_index + 1,
                "text": page.get_text("text", sort=True).strip(),
                "blocks": blocks,
                "page_width": width,
                "page_height": height,
            })
    return document, slides
