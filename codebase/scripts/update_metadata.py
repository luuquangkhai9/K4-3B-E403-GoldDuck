"""Add learning-day metadata to an existing index without running Vision/E5."""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from app.paths import load_environment
import pymupdf
from app.ingestion.index import write_slide_index
from app.ingestion.metadata import build_day_catalog, enrich_slide_metadata, record_day_metadata
from app.viewer.evidence import resolve_pdf


def update_metadata(pdf_dir, index_path):
    index_path = Path(index_path)
    payload = json.loads(index_path.read_text(encoding="utf-8-sig"))
    records = payload.get("slides") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ValueError("Index must contain a slide list")
    documents = {}
    updated = []
    for record in records:
        filename = record["filename"]
        if filename not in documents:
            with pymupdf.open(resolve_pdf(Path(pdf_dir), filename)) as pdf:
                document = {"filename": filename, "title": (pdf.metadata or {}).get("title") or Path(filename).stem,
                            "total_pages": len(pdf), **record_day_metadata(record)}
            documents[filename] = document
        document = documents[filename]
        if record_day_metadata(record)["day_id"] != document["day_id"]:
            raise ValueError("Document slides have inconsistent learning days")
        if type(record.get("page_number")) is not int or not 1 <= record["page_number"] <= document["total_pages"]:
            raise ValueError("Slide page is outside its PDF")
        updated.append(enrich_slide_metadata(record, document))
    catalog = build_day_catalog(updated)
    if isinstance(payload, dict):
        payload = {**payload, "slides": updated}
    else:
        payload = updated
    if updated != records:
        write_slide_index(index_path, payload)
    return {"documents": len(documents), "slides": len(updated), "days": len(catalog["days"]),
            "unassigned_documents": catalog["unassigned_document_count"],
            "vision": dict(Counter(s.get("visual_analysis", {}).get("status", "missing") for s in updated)),
            "updated": updated != records, "index": str(index_path)}


def main():
    data_root = load_environment(ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-dir", default=os.getenv("PDF_DIR", "data/pdf"))
    parser.add_argument("--index-dir", default=os.getenv("INDEX_DIR", "data/index"))
    args = parser.parse_args()
    pdf_dir, index_dir = Path(args.pdf_dir), Path(args.index_dir)
    pdf_dir = pdf_dir if pdf_dir.is_absolute() else data_root / pdf_dir
    index_dir = index_dir if index_dir.is_absolute() else data_root / index_dir
    try:
        result = update_metadata(pdf_dir, index_dir / "slides.json")
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        print(f"Metadata update failed ({type(exc).__name__}); existing index preserved.", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
