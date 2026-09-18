"""Learning-day inference and safe migration of an enriched index."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pymupdf

from .ingest import ingest_pdfs
from .metadata import infer_day_id, normalize_day_id
from .parser import parse_pdf
from app.retrieval.dense import DenseIndex
from scripts.update_metadata import update_metadata


class LearningDayMetadataTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"VISION_ENABLED": "false"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.pdf_dir = self.root / "pdf"
        self.output = self.root / "index/slides.json"
        for filename in ("Day01/a.pdf", "Day01/b.pdf", "Day02/a.pdf", "unknown.pdf"):
            path = self.pdf_dir / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            with pymupdf.open() as pdf:
                page = pdf.new_page()
                page.insert_text((40, 80), "Matrix normalization")
                pdf.set_metadata({"title": "Lecture " + filename})
                pdf.save(path)

    def test_canonical_aliases_and_invalid_days(self):
        for value in ("Day01", "DAY 1", "D01", "1", 1, " day-001 "):
            self.assertEqual(normalize_day_id(value), "Day01")
        for value in (None, True, 0, "", "Day00", "Day-1.5", "Day1/Day2", [], "other"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_day_id(value)

    def test_directory_priority_windows_paths_filename_fallback_and_unknown(self):
        cases = {"Day01/Day02-lecture.pdf": "Day01", "root/day 02/sub/lecture.pdf": "Day02",
                 "Day01/archive/Day03/lecture.pdf": "Day03", r"Day04\lesson.pdf": "Day04",
                 "1-Day 08 Lecture.pdf": "Day08", "huydd-day04-slides.pdf": "Day04",
                 "lecture-day01-and-day02.pdf": None, "Day00/lecture.pdf": None,
                 "Monday/lecture.pdf": None, "day01slide.pdf": None}
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                self.assertEqual(infer_day_id(filename), expected)

    def test_ingestion_groups_multiple_files_and_carries_document_metadata(self):
        result = ingest_pdfs(self.pdf_dir, self.output)
        first = result["catalog"]["days"][0]
        self.assertEqual((first["day_id"], first["day_number"], first["document_count"], first["slide_count"]),
                         ("Day01", 1, 2, 2))
        records = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(len({s["document_id"] for s in records}), 4)
        for slide in records:
            self.assertEqual(slide["document_title"], "Lecture " + slide["filename"])
            self.assertEqual(slide["document_total_pages"], 1)
        self.assertEqual(result["catalog"]["unassigned_document_count"], 1)
        document, slides = parse_pdf(self.pdf_dir / "Day01/a.pdf")
        self.assertEqual(document["day_id"], "Day01")
        self.assertEqual(slides[0]["day_label"], "Day 01")

    def legacy_index(self):
        ingest_pdfs(self.pdf_dir, self.output)
        slides = json.loads(self.output.read_text(encoding="utf-8"))
        keys = {"day_id", "day_number", "day_label", "document_title", "document_total_pages"}
        slides = [{k: v for k, v in slide.items() if k not in keys} for slide in slides]
        slides[0]["visual_analysis"] = {"status": "success", "summary": "Visible matrix"}
        slides[0]["retrieval_text"] = slides[0]["text"] + "\nVisible matrix"
        # Keep compatibility with the older object envelope as well as lists.
        self.output.write_text(json.dumps({"slides": slides, "version": "legacy"}), encoding="utf-8")
        return slides

    def test_migration_preserves_vision_ids_quotes_bbox_and_embeddings_and_is_idempotent(self):
        original = self.legacy_index()
        fingerprint = DenseIndex(original, self.output.parent).fingerprint
        with patch("app.ingestion.vision.VisionAdapter.analyze", side_effect=AssertionError("No paid API")), patch(
            "app.retrieval.dense.DenseIndex._initialize", side_effect=AssertionError("No embedding inference")
        ):
            result = update_metadata(self.pdf_dir, self.output)
        payload = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], "legacy")
        for before, after in zip(original, payload["slides"]):
            self.assertEqual(before, {k: after[k] for k in before})
        self.assertEqual(fingerprint, DenseIndex(payload["slides"], self.output.parent).fingerprint)
        self.assertEqual((result["days"], result["documents"], result["slides"]), (2, 4, 4))
        stamp = self.output.stat().st_mtime_ns
        self.assertFalse(update_metadata(self.pdf_dir, self.output)["updated"])
        self.assertEqual(stamp, self.output.stat().st_mtime_ns)

    def test_migration_failure_preserves_index(self):
        self.legacy_index()
        original = self.output.read_bytes()
        (self.pdf_dir / "Day02/a.pdf").unlink()
        with self.assertRaises(FileNotFoundError):
            update_metadata(self.pdf_dir, self.output)
        self.assertEqual(self.output.read_bytes(), original)
