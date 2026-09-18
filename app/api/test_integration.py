"""Exercise real ingestion -> lexical retrieval -> extractive QA -> source routes."""

import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pymupdf
import httpx
from fastapi.testclient import TestClient

from app.api.main import app
from app.ingestion.ingest import ingest_pdfs
from app.qa.generator import AnswerGenerator
from app.qa.service import QAService
from app.retrieval.service import RetrievalService


class DemoIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.pdf_dir = root / "pdf"
        self.pdf_dir.mkdir()
        self.index_dir = root / "index"
        self.filename = "bài giảng mẫu.pdf"
        self.passages = [
            "Gradient descent updates parameters using the negative gradient.",
            "Overfitting occurs when a model memorizes training examples.",
            "Regularization penalizes model complexity to improve generalization.",
            "Backpropagation computes derivatives through the chain rule.",
            "Convolution applies a shared kernel across spatial positions.",
        ]
        with pymupdf.open() as document:
            for number, text in enumerate(self.passages):
                page = document.new_page(width=600, height=400)
                page.insert_text((40, 80), text, fontsize=12)
                if number == 4:
                    page.set_rotation(90)
            document.save(self.pdf_dir / self.filename)
        ingest_pdfs(self.pdf_dir, self.index_dir / "slides.json")
        self.environment = patch.dict(os.environ, {"PDF_DIR": str(self.pdf_dir), "TOP_K": "5"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.previous = {
            name: getattr(app.state, name, None)
            for name in ("retrieval_service", "qa_service")
        }
        self.addCleanup(self.restore_services)
        app.state.retrieval_service = RetrievalService(index_dir=self.index_dir, dense_enabled=False)
        app.state.qa_service = QAService(generator=AnswerGenerator(api_key=""))
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def restore_services(self):
        for name, service in self.previous.items():
            if service is None:
                delattr(app.state, name)
            else:
                setattr(app.state, name, service)

    def test_health_and_ui(self):
        self.assertEqual(self.client.get("/api/health").json(), {"status": "ok"})
        self.assertIn("Hỏi đáp bài giảng", self.client.get("/").text)
        self.assertEqual(self.client.get("/static/app.js").status_code, 200)

    def test_five_questions_reach_exact_pages_and_quotes(self):
        questions = [
            "Gradient descent là gì?", "Overfitting là gì?", "Regularization là gì?",
            "Backpropagation là gì?", "Convolution là gì?",
        ]
        for expected_page, question in enumerate(questions, start=1):
            with self.subTest(question=question):
                response = self.client.post("/api/ask", json={"question": question})
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                citation = result["citations"][0]
                self.assertIn("[E1]", result["answer"])
                self.assertEqual(citation["filename"], self.filename)
                self.assertEqual(citation["page_number"], expected_page)
                self.assertEqual(citation["quote"], self.passages[expected_page - 1])
                self.assertIn(citation["quote"], result["answer"])
                params = parse_qs(urlsplit(citation["viewer_url"]).query)
                self.assertEqual(params["page"], [str(expected_page)])
                self.assertEqual(params["file"], [self.filename])
                self.assertEqual([float(v) for v in params["bbox"][0].split(",")], citation["bbox"])
                self.assertTrue(all(0 <= v <= 1 for v in citation["bbox"]))
                self.assertEqual(self.client.get(citation["viewer_url"]).status_code, 200)
                image = self.client.get("/api/page", params={"file": self.filename, "page": expected_page})
                self.assertEqual(image.status_code, 200)
                self.assertTrue(image.content.startswith(b"\x89PNG"))
                if expected_page == 5:
                    pixmap = pymupdf.Pixmap(image.content)
                    self.assertGreater(pixmap.height, pixmap.width)

    def test_empty_corpus_returns_insufficient_evidence(self):
        app.state.retrieval_service = RetrievalService(index_dir=self.index_dir / "missing", dense_enabled=False)
        result = self.client.post("/api/ask", json={"question": "Gradient descent là gì?"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["citations"], [])
        self.assertIn("Không tìm thấy đủ thông tin", result.json()["answer"])

    def test_question_validation(self):
        for payload in ({"question": "   "}, {}, {"question": "x" * 4001}):
            self.assertEqual(self.client.post("/api/ask", json=payload).status_code, 422)

    def test_missing_or_invalid_sources(self):
        for filename in ("../outside.pdf", str(self.pdf_dir / self.filename), "../README.md"):
            with self.subTest(filename=filename):
                response = self.client.get("/api/page", params={"file": filename, "page": 1})
                self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/api/page", params={"file": "missing.pdf", "page": 1}).status_code, 404)
        self.assertEqual(self.client.get("/api/page", params={"file": self.filename, "page": 6}).status_code, 404)
        self.assertEqual(self.client.get("/api/page", params={"file": self.filename, "page": 0}).status_code, 422)

    def test_original_pdf(self):
        response = self.client.get("/pdf/" + self.filename)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn("inline", response.headers["content-disposition"])

    def test_run_demo_command(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        environment = dict(os.environ, HOST="127.0.0.1", PORT=str(port),
                           DENSE_ENABLED="false", OPENAI_API_KEY="", INDEX_DIR=str(self.index_dir))
        script = Path(__file__).resolve().parents[2] / "scripts" / "run_demo.py"
        process = subprocess.Popen([sys.executable, str(script)], cwd=self.temporary.name,
                                   env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=2, trust_env=False) as client:
                deadline = time.monotonic() + 15
                while True:
                    self.assertIsNone(process.poll(), "Demo exited before serving HTTP")
                    try:
                        response = client.get("/api/health")
                        if response.status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    if time.monotonic() > deadline:
                        self.fail("Demo did not start within 15 seconds")
                    time.sleep(0.1)
                self.assertEqual(response.json(), {"status": "ok"})
                result = client.post("/api/ask", json={"question": "Gradient descent là gì?"})
                self.assertEqual(result.status_code, 200, result.text)
                citation = result.json()["citations"][0]
                self.assertEqual(citation["page_number"], 1)
                self.assertEqual(client.get(citation["viewer_url"]).status_code, 200)
        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
