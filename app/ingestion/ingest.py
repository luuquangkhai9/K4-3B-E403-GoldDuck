"""Discover PDFs and atomically replace the slide index."""

import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
import logging
import os
from pathlib import Path
import tempfile

from .models import SlideRecord
from .parser import parse_pdf
from .vision import VisionConfig, VisionEnricher

logger = logging.getLogger(__name__)


def discover_pdfs(pdf_dir: str | Path) -> list[Path]:
    directory = Path(pdf_dir)
    if not directory.exists():
        raise FileNotFoundError(f"PDF directory does not exist: {directory}")
    if not directory.is_dir():
        raise ValueError(f"PDF directory is not a directory: {directory}")
    return sorted(
        (path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() == ".pdf"),
        key=lambda path: path.relative_to(directory).as_posix(),
    )


def ingest_pdfs(
    pdf_dir: str | Path = "data/pdf",
    output_path: str | Path = "data/index/slides.json",
    *,
    vision_config: VisionConfig | None = None,
    vision_adapter=None,
    vision_workers: int = 1,
) -> dict:
    if type(vision_workers) is not int or not 1 <= vision_workers <= 8:
        raise ValueError("Vision workers must be an integer between 1 and 8")
    directory, output = Path(pdf_dir), Path(output_path)
    try:
        config = vision_config if vision_config is not None else VisionConfig.from_env()
    except (ValueError, TypeError):
        logger.warning("Invalid Vision configuration; Vision disabled")
        config = VisionConfig()
    slides: list[SlideRecord] = []
    errors: list[dict[str, str]] = []
    documents = []
    paths = discover_pdfs(directory)
    pool = ThreadPoolExecutor(max_workers=vision_workers) if config.enabled and vision_workers > 1 else nullcontext()
    with pool as executor:
        vision = VisionEnricher(config, output.parent / "vision", vision_adapter, executor=executor) if config.enabled else None
        for position, path in enumerate(paths, 1):
            filename = path.relative_to(directory).as_posix()
            try:
                document, records = parse_pdf(path, filename=filename, vision=vision)
            except (OSError, ValueError, RuntimeError) as exc:
                logger.error("Cannot ingest %s: %s", filename, exc)
                errors.append({"filename": filename, "error": str(exc)})
                continue
            documents.append(document)
            slides.extend(records)
            logger.info("Parsed PDF %d/%d (%d slides): %s", position, len(paths), len(records), filename)
        if vision is not None:
            vision.finish()
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
    statuses = Counter(slide.get("visual_analysis", {}).get("status", "disabled") for slide in slides)
    return {"documents": documents, "slides": len(slides), "errors": errors, "output": str(output), "vision": dict(statuses)}
