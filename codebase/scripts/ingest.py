"""Run with python scripts/ingest.py from any working directory."""

import argparse
import logging
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.ingestion.ingest import ingest_pdfs
from dotenv import load_dotenv
from app.paths import load_environment


def main() -> int:
    data_root = load_environment(PROJECT_ROOT)
    parser = argparse.ArgumentParser(description="Extract lecture PDF slides and normalized text boxes.")
    parser.add_argument("--pdf-dir", default=os.getenv("PDF_DIR", "data/pdf"))
    parser.add_argument("--index-dir", default=os.getenv("INDEX_DIR", "data/index"))
    parser.add_argument("--vision-workers", type=int, choices=range(1, 9), default=1,
                        help="Concurrent Vision requests (1-8); PDF rendering stays sequential.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    pdf_dir, index_dir = Path(args.pdf_dir), Path(args.index_dir)
    if not pdf_dir.is_absolute():
        pdf_dir = data_root / pdf_dir
    if not index_dir.is_absolute():
        index_dir = data_root / index_dir
    try:
        result = ingest_pdfs(pdf_dir, index_dir / "slides.json", vision_workers=args.vision_workers)
    except (OSError, ValueError, RuntimeError) as exc:
        logging.error("Ingestion failed: %s", exc)
        return 1
    print(f"Indexed {len(result['documents'])} PDFs, {result['slides']} slides -> {result['output']}")
    print(f"Vision: {result['vision']}")
    if result["vision"].get("failed", 0):
        logging.error("Some slides failed Vision; native text was preserved. Rerun ingestion to retry failed slides using the cache.")
    if not result["documents"]:
        logging.warning("No PDFs found in %s. Wrote an empty slide index.", pdf_dir)
    return 1 if result["errors"] or result["vision"].get("failed", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
