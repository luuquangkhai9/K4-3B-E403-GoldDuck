"""Discover PDFs and atomically replace the slide index."""

import json
import logging
import os
from pathlib import Path
import tempfile

from .models import SlideRecord
from .parser import parse_pdf

logger = logging.getLogger(__name__)


def discover_pdfs(pdf_dir: str | Path) -> list[Path]:
    directory = Path(pdf_dir)
    if not directory.exists():
        return []
    if not directory.is_dir():
        raise ValueError(f"PDF directory is not a directory: {directory}")
    return sorted(
        (path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() == ".pdf"),
        key=lambda path: path.relative_to(directory).as_posix(),
    )


def ingest_pdfs(
    pdf_dir: str | Path = "data/pdf",
    output_path: str | Path = "data/index/slides.json",
) -> dict:
    directory, output = Path(pdf_dir), Path(output_path)
    slides: list[SlideRecord] = []
    errors: list[dict[str, str]] = []
    documents = []
    paths = discover_pdfs(directory)
    for path in paths:
        filename = path.relative_to(directory).as_posix()
        try:
            document, records = parse_pdf(path, filename=filename)
        except (OSError, ValueError, RuntimeError) as exc:
            logger.error("Cannot ingest %s: %s", filename, exc)
            errors.append({"filename": filename, "error": str(exc)})
            continue
        documents.append(document)
        slides.extend(records)
    # A totally failed run must not destroy a previously usable index.
    if paths and not documents:
        raise RuntimeError("All PDFs failed ingestion; existing index was preserved.")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent, suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(slides, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
        os.replace(temporary, output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return {"documents": documents, "slides": len(slides), "errors": errors, "output": str(output)}
