"""Regression checks for preserving indexes and the ingestion command."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pymupdf

from .ingest import ingest_pdfs


class IngestionTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {"VISION_ENABLED": "false"})
        environment.start()
        self.addCleanup(environment.stop)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.pdf_dir = self.root / "pdf"
        self.pdf_dir.mkdir()
        self.output = self.root / "index" / "slides.json"
        self.output.parent.mkdir()
        self.previous = '[{"previous": true}]\n'
        self.output.write_text(self.previous, encoding="utf-8")

    def test_missing_directory_preserves_existing_index(self):
        with self.assertRaises(FileNotFoundError):
            ingest_pdfs(self.root / "missing", self.output)
        self.assertEqual(self.output.read_text(encoding="utf-8"), self.previous)

    def test_failed_pdfs_preserve_existing_index(self):
        (self.pdf_dir / "broken.pdf").write_bytes(b"invalid PDF")
        with self.assertRaises(RuntimeError):
            ingest_pdfs(self.pdf_dir, self.output)
        self.assertEqual(self.output.read_text(encoding="utf-8"), self.previous)

    def test_existing_empty_directory_writes_empty_index(self):
        result = ingest_pdfs(self.pdf_dir, self.output)
        self.assertEqual(result["slides"], 0)
        self.assertEqual(json.loads(self.output.read_text(encoding="utf-8")), [])

    def test_command_loads_paths_from_dotenv(self):
        from scripts import ingest

        (self.root / ".env").write_text("PDF_DIR=pdf\nINDEX_DIR=index\n", encoding="utf-8")
        with patch.object(ingest, "PROJECT_ROOT", self.root), patch.dict(os.environ, {}, clear=True), patch.object(sys, "argv", ["ingest.py"]):
            self.assertEqual(ingest.main(), 0)
        self.assertEqual(json.loads(self.output.read_text(encoding="utf-8")), [])

    def test_command_from_another_working_directory(self):
        nested = self.pdf_dir / "lectures"
        nested.mkdir()
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text((40, 80), "Gradient descent updates parameters.")
            pdf.save(nested / "lecture.PDF")
        script = Path(__file__).resolve().parents[2] / "scripts" / "ingest.py"
        result = subprocess.run(
            [sys.executable, str(script)], cwd=self.root,
            env=dict(os.environ, PDF_DIR=str(self.pdf_dir), INDEX_DIR=str(self.output.parent)),
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        records = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(records[0]["filename"], "lectures/lecture.PDF")
        self.assertEqual(records[0]["page_number"], 1)
        self.assertIn("Gradient descent", records[0]["text"])

    def test_command_reports_vision_failure_while_preserving_native_text(self):
        from scripts import ingest
        from .vision import VisionConfig

        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text((40, 80), "CNN")
            pdf.save(self.pdf_dir / "visual.pdf")
        arguments = ["ingest.py", "--pdf-dir", str(self.pdf_dir), "--index-dir", str(self.output.parent)]
        with patch.object(sys, "argv", arguments), patch(
            "app.ingestion.ingest.VisionConfig.from_env", return_value=VisionConfig(enabled=True, model="test")
        ), patch("app.ingestion.vision.VisionAdapter.analyze", side_effect=TimeoutError("hidden")):
            self.assertEqual(ingest.main(), 1)
        slide = json.loads(self.output.read_text(encoding="utf-8"))[0]
        self.assertEqual(slide["text"], "CNN")
        self.assertEqual(slide["retrieval_text"], "CNN")
        self.assertEqual(slide["visual_analysis"]["status"], "failed")
