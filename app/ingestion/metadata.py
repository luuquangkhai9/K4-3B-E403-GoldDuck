"""Learning-day metadata and catalogs derived from the slide index."""

import hashlib
from pathlib import PurePosixPath
import re


def normalize_day_id(value):
    """Accept Day01, day 1, D01 or 1; reject empty or invalid filters."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("Invalid learning day")
    match = re.fullmatch(r"(?:day|d)?[\s_-]*(\d{1,4})", str(value).strip(), re.I)
    if not match or int(match[1]) < 1:
        raise ValueError("Learning day must be a positive day number, e.g. Day01")
    return f"Day{int(match[1]):02d}"


def infer_day_id(filename):
    """Nearest Day directory wins; otherwise use an unambiguous filename token."""
    path = PurePosixPath(filename.replace("\\", "/"))
    for part in reversed(path.parts[:-1]):
        if re.fullmatch(r"(?:day|d)[\s_-]*\d{1,4}", part, re.I):
            try:
                return normalize_day_id(part)
            except ValueError:
                continue
    tokens = re.findall(r"(?<![a-z0-9])(?:day|d)[\s_-]*(\d{1,4})(?![a-z0-9])", path.stem, re.I)
    days = {normalize_day_id(token) for token in tokens if int(token) > 0}
    return next(iter(days)) if len(days) == 1 else None


def normalize_scope(scope):
    """Canonical Day IDs; an empty list means the whole course."""
    if scope is None:
        return None
    if not isinstance(scope, (list, tuple)):
        raise ValueError("Scope must be a list of learning days")
    days = list(dict.fromkeys(normalize_day_id(day) for day in scope))
    return days or None


def resolve_day_scope(day_id=None, scope=None):
    """Intersect the legacy single-day filter with a multi-day selection."""
    days = normalize_scope(scope)
    if day_id is not None:
        canonical = normalize_day_id(day_id)
        if days is not None and canonical not in days:
            raise ValueError("Ngày học không nằm trong phạm vi đã chọn.")
        return [canonical]
    return days


def day_metadata(day_id):
    canonical = normalize_day_id(day_id) if day_id is not None else None
    number = int(canonical[3:]) if canonical is not None else None
    return {"day_id": canonical, "day_number": number,
            "day_label": f"Day {number:02d}" if number is not None else None}


def record_day_metadata(record):
    metadata = day_metadata(record.get("day_id") if "day_id" in record else infer_day_id(record["filename"]))
    if "day_number" in record and (
        record["day_number"] != metadata["day_number"]
        or (record["day_number"] is not None and type(record["day_number"]) is not int)
    ):
        raise ValueError("day_number does not match day_id")
    return metadata


def enrich_slide_metadata(slide, document=None):
    result = dict(slide)
    result.update(record_day_metadata(document if document is not None else slide))
    result["day"] = result["day_id"]
    filename = slide["filename"]
    result.setdefault("document_id", "doc_" + hashlib.sha256(filename.encode("utf-8")).hexdigest()[:16])
    result["document_title"] = document["title"] if document is not None else slide.get(
        "document_title", PurePosixPath(filename.replace("\\", "/")).stem)
    if not isinstance(result["document_id"], str) or not result["document_id"].strip():
        raise ValueError("document_id must be a nonempty string")
    if not isinstance(result["document_title"], str):
        raise ValueError("document_title must be a string")
    if document is not None:
        result["document_total_pages"] = document["total_pages"]
    return result


def build_day_catalog(records):
    documents = {}
    for slide in records:
        filename = slide["filename"]
        document = documents.setdefault(filename, {
            "document_id": slide["document_id"], "filename": filename,
            "title": slide["document_title"], **record_day_metadata(slide),
            "total_pages": slide.get("document_total_pages", 0),
            "indexed_slides": 0, "searchable_slides": 0,
        })
        if document["day_id"] != slide["day_id"] or document["document_id"] != slide["document_id"]:
            raise ValueError("Document slides have inconsistent metadata")
        document["total_pages"] = max(document["total_pages"], slide["page_number"])
        document["indexed_slides"] += 1
        text = slide.get("retrieval_text")
        if not isinstance(text, str) or not text.strip():
            text = slide.get("text", "")
        document["searchable_slides"] += bool(text.strip())
    days = {}
    unassigned = []
    for document in sorted(documents.values(), key=lambda d: d["filename"]):
        if document["day_id"] is None:
            unassigned.append(document)
            continue
        day = days.setdefault(document["day_id"], {
            **day_metadata(document["day_id"]), "document_count": 0,
            "slide_count": 0, "searchable_slide_count": 0, "documents": [],
        })
        day["documents"].append(document)
        day["document_count"] += 1
        day["slide_count"] += document["indexed_slides"]
        day["searchable_slide_count"] += document["searchable_slides"]
    return {"days": sorted(days.values(), key=lambda d: d["day_number"]),
            "unassigned_documents": unassigned,
            "unassigned_document_count": len(unassigned),
            "unassigned_slide_count": sum(d["indexed_slides"] for d in unassigned)}
