"""Build source links carrying their own coordinates, without global E1 state."""

import math
from pathlib import Path
from urllib.parse import urlencode


def normalized_bbox(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        box = [float(v) for v in value]
    except (ValueError, TypeError):
        return None
    if not all(math.isfinite(v) and 0 <= v <= 1 for v in box):
        return None
    if box[0] >= box[2] or box[1] >= box[3]:
        return None
    return box


def viewer_url(citation: dict) -> str:
    params = {
        "file": citation["filename"],
        "page": citation["page_number"],
        "evidence": citation["evidence_id"],
    }
    box = normalized_bbox(citation.get("bbox"))
    if box:
        params["bbox"] = ",".join(str(v) for v in box)
    return "/viewer?" + urlencode(params)


def resolve_pdf(root: Path, filename: str) -> Path:
    """Allow nested PDFs, but reject traversal, absolute paths, and symlink escapes."""
    root = root.resolve()
    if not filename or Path(filename).is_absolute():
        raise ValueError("Tên tài liệu không hợp lệ.")
    target = (root / filename).resolve()
    if not target.is_relative_to(root) or target.suffix.lower() != ".pdf":
        raise ValueError("Tên tài liệu không hợp lệ.")
    if not target.is_file():
        raise FileNotFoundError(filename)
    return target
