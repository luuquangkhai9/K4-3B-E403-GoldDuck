"""Run with python scripts/ingest.py from any working directory."""

import argparse
import logging
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.ingestion.ingest import ingest_pdfs


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract lecture PDF slides and normalized text boxes.")
    parser.add_argument("--pdf-dir", default=os.getenv("PDF_DIR", "data/pdf"))
    parser.add_argument("--index-dir", default=os.getenv("INDEX_DIR", "data/index"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    pdf_dir, index_dir = Path(args.pdf_dir), Path(args.index_dir)
    if not pdf_dir.is_absolute():
        pdf_dir = PROJECT_ROOT / pdf_dir
    if not index_dir.is_absolute():
        index_dir = PROJECT_ROOT / index_dir
    try:
        result = ingest_pdfs(pdf_dir, index_dir / "slides.json")
    except (OSError, ValueError, RuntimeError) as exc:
        logging.error("Ingestion failed: %s", exc)
        return 1
    print(f"Indexed {len(result['documents'])} PDFs, {result['slides']} slides -> {result['output']}")
    if not result["documents"]:
        logging.warning("No PDFs found in %s. Wrote an empty slide index.", pdf_dir)
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
