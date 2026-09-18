"""Exercise real ingestion -> lexical retrieval -> extractive QA -> source routes."""

import os
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import types
from unittest.mock import Mock, patch
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
        environment = patch.dict(os.environ, {
            "VISION_ENABLED": "false", "RERANK_ENABLED": "false",
            "NEIGHBOR_EXPANSION_ENABLED": "false", "NO_ANSWER_THRESHOLD": "",
            "NO_ANSWER_ENABLED": "true", "CITATION_VALIDATION_ENABLED": "true",
            "EVIDENCE_TOP_K": "5", "MAX_EVIDENCE_PER_SLIDE": "2",
        })
        environment.start()
        self.addCleanup(environment.stop)
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
        for filename in ("../outside.pdf", str(self.pdf_dir / self.filename), "../README.md", "bad\x00.pdf"):
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

    def test_visual_evidence_reaches_real_qa_and_viewer(self):
        from app.ingestion.vision import VisionConfig

        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.draw_rect((40, 40, 200, 150), fill=(0.2, 0.4, 0.8))
            pdf.save(self.pdf_dir / "diagram.pdf")
        adapter = Mock()
        adapter.analyze.return_value = {
            "summary": "Blue rectangular diagram element.", "concepts": ["diagram"],
            "relationships": [], "visible_text_not_in_pdf": [],
        }
        ingest_pdfs(self.pdf_dir, self.index_dir / "slides.json",
                    vision_config=VisionConfig(enabled=True, model="test", text_threshold=1),
                    vision_adapter=adapter)
        response = self.client.post("/api/ask", json={"question": "Blue rectangular diagram?"})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertIn("Blue rectangular diagram element.", result["answer"])
        citation = result["citations"][0]
        self.assertEqual(citation["filename"], "diagram.pdf")
        self.assertEqual(citation["evidence_type"], "visual")
        self.assertTrue(citation["vision_used"])
        self.assertIsNone(citation["bbox"])
        self.assertEqual(self.client.get(citation["viewer_url"]).status_code, 200)
        self.assertEqual(self.client.get("/api/page", params={"file": "diagram.pdf", "page": 1}).status_code, 200)
        unrelated = self.client.post("/api/ask", json={"question": "xyzzyunknown"}).json()
        self.assertTrue(unrelated["grounding"]["no_answer"])

    def test_repeated_quote_preserves_each_block_metadata(self):
        evidence = [
            {"evidence_id": f"E{i}", "slide_id": "slide1", "block_id": f"block{i}",
             "filename": self.filename, "page_number": 1, "quote": "Repeated text",
             "bbox": [0.1, i * 0.1, 0.8, i * 0.1 + 0.05], "block_score": i * 0.3}
            for i in (1, 2)
        ]
        retrieval = Mock()
        retrieval.retrieve.return_value = {"slides": [], "evidence": evidence}
        with patch("app.api.main.get_services", return_value=(retrieval, app.state.qa_service)):
            response = self.client.post("/api/ask", json={"question": "Repeated text?"})
        self.assertEqual(response.status_code, 200, response.text)
        for citation, source in zip(response.json()["citations"], evidence):
            self.assertEqual(citation["block_id"], source["block_id"])
            self.assertEqual(citation["block_score"], source["block_score"])

    def test_full_v2_pipeline_with_offline_providers(self):
        import numpy as np
        from app.ingestion.vision import VisionConfig

        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.draw_rect((40, 40, 200, 150), fill=(0.2, 0.4, 0.8))
            page = pdf.new_page()
            page.insert_text((40, 80), "Kernel filters extract local features.")
            pdf.save(self.pdf_dir / "cnn.pdf")
        adapter = Mock()
        adapter.analyze.return_value = {
            "summary": "CNN diagram shows convolution and pooling.", "concepts": ["CNN"],
            "relationships": ["Input -> Convolution -> Pooling"], "visible_text_not_in_pdf": [],
        }
        ingest_pdfs(self.pdf_dir, self.index_dir / "slides.json",
                    vision_config=VisionConfig(enabled=True, model="test", text_threshold=1),
                    vision_adapter=adapter)
        fake_module = types.ModuleType("sentence_transformers")

        class FakeModel:
            def __init__(self, *args, **kwargs):
                pass

            def encode(self, texts, **kwargs):
                # Controlled semantic scores test stage integration only.
                vectors = np.zeros((len(texts), 384), dtype=np.float32)
                for row, text in enumerate(texts):
                    text = text.casefold()
                    topic = any(word in text for word in ("cnn", "convolution", "kernel", "tích chập"))
                    vectors[row, 0 if topic else 2 if text.startswith("query:") else 1] = 1
                return vectors

        fake_module.SentenceTransformer = FakeModel

        def fake_rerank(request, **kwargs):
            payload = json.loads(request.data)
            index = next(i for i, text in enumerate(payload["documents"])
                         if "Document: cnn.pdf\nPage: 1\n" in text)
            return io.StringIO(json.dumps({"results": [{"index": index, "relevance_score": 0.9}]}))

        config = {
            "VISION_ENABLED": "true", "RERANK_ENABLED": "true", "RERANK_PROVIDER": "cohere",
            "RERANK_API_KEY": "fake", "RERANK_MODEL": "test", "RERANK_TOP_K": "1",
            "NEIGHBOR_EXPANSION_ENABLED": "true", "NEIGHBOR_DISTANCE": "1",
            "EVIDENCE_TOP_K": "2", "MAX_EVIDENCE_PER_SLIDE": "1",
            "NO_ANSWER_ENABLED": "true", "NO_ANSWER_THRESHOLD": "0.5",
            "CITATION_VALIDATION_ENABLED": "true",
        }
        with patch.dict(os.environ, config), patch.dict("sys.modules", {"sentence_transformers": fake_module}), \
             patch("app.retrieval.rerank.urlopen", side_effect=fake_rerank):
            app.state.retrieval_service = RetrievalService(self.index_dir, dense_enabled=True, dense_isolated=False)
            generator = Mock(available=True)
            generator.generate.return_value = "Convolution và pooling [E1]; kernel filters [E2]."
            app.state.qa_service = QAService(generator=generator)
            response = self.client.post("/api/ask", json={"question": "Mạng tích chập gồm gì?"})
            self.assertEqual(response.status_code, 200, response.text)
            result = response.json()
            self.assertTrue(result["debug"]["reranker_used"])
            self.assertEqual(result["debug"]["block_ranking_method"], "e5")
            self.assertEqual([c["source_role"] for c in result["citations"]], ["primary", "neighbor"])
            self.assertEqual([c["page_number"] for c in result["citations"]], [1, 2])
            self.assertEqual(result["citations"][0]["evidence_type"], "visual")
            for citation in result["citations"]:
                self.assertEqual(self.client.get(citation["viewer_url"]).status_code, 200)
            abstention = self.client.post("/api/ask", json={"question": "xyzzyunknown"})
            self.assertEqual(abstention.status_code, 200, abstention.text)
            self.assertTrue(abstention.json()["grounding"]["no_answer"])
            self.assertEqual(abstention.json()["citations"], [])
            generator.generate.assert_called_once()

    def test_run_demo_command(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        environment = dict(os.environ, HOST="127.0.0.1", PORT=str(port),
                           DENSE_ENABLED="false", OPENAI_API_KEY="", INDEX_DIR=str(self.index_dir),
                           RERANK_ENABLED="false", VISION_ENABLED="false")
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


class V2ContractTests(unittest.TestCase):
    """Validate integration independently of parallel implementation of V2 services."""

    def test_v1_and_v2_metadata_and_five_smoke_contracts(self):
        questions = [
            "Học máy là gì?", "Gradient descent là gì?", "Sơ đồ CNN có gì?",
            "Slide tiếp theo giải thích điều gì?", "Thông tin ngoài bài giảng?",
        ]
        switches = ("VISION_ENABLED", "RERANK_ENABLED", "NEIGHBOR_EXPANSION_ENABLED",
                    "CITATION_VALIDATION_ENABLED", "NO_ANSWER_ENABLED")
        for enabled in (False, True):
            for index, question in enumerate(questions):
                with self.subTest(enabled=enabled, question=question):
                    evidence = {"evidence_id": "E9", "filename": "lecture.pdf", "page_number": 2,
                                "quote": "Nội dung nguồn", "bbox": [0.1, 0.2, 0.8, 0.7]}
                    retrieved = {"slides": [], "evidence": [evidence]}
                    result = {"answer": "Nội dung nguồn [E1]", "citations": [dict(evidence, evidence_id="E1")]}
                    if enabled:
                        evidence.update(slide_id="slide2", block_id="block2", block_score=0.9,
                                        source_role="neighbor" if index == 3 else "primary")
                        retrieved.update(debug={"reranker_used": True}, context_slides=[
                            {"slide_id": "slide2", "visual_analysis": {"status": "success" if index == 2 else "skipped"}}])
                        result["grounding"] = {"status": "grounded", "no_answer": False}
                    if index == 4:
                        retrieved["evidence"] = []
                        result = {"answer": "Không tìm thấy đủ thông tin trong kho bài giảng để trả lời câu hỏi này.", "citations": []}
                        if enabled:
                            result["grounding"] = {"status": "insufficient_evidence", "no_answer": True}
                    retrieval, qa = Mock(), Mock()
                    retrieval.retrieve.return_value = retrieved
                    qa.answer.return_value = result
                    with patch.dict(os.environ, {"TOP_K": "5", **{key: str(enabled).lower() for key in switches}}), \
                         patch("app.api.main.get_services", return_value=(retrieval, qa)), TestClient(app) as client:
                        response = client.post("/api/ask", json={"question": question})
                    self.assertEqual(response.status_code, 200, response.text)
                    data = response.json()
                    self.assertEqual(data["answer"], result["answer"])
                    if index == 4:
                        self.assertEqual(data["citations"], [])
                        if enabled:
                            self.assertTrue(data["grounding"]["no_answer"])
                        continue
                    citation = data["citations"][0]
                    self.assertEqual(citation["evidence_id"], "E1")
                    self.assertEqual(citation["bbox"], evidence["bbox"])
                    self.assertEqual(parse_qs(urlsplit(citation["viewer_url"]).query)["evidence"], ["E1"])
                    if enabled:
                        self.assertEqual(citation["source_role"], evidence["source_role"])
                        self.assertEqual(citation["block_score"], 0.9)
                        self.assertEqual(citation["vision_used"], index == 2)
                        self.assertTrue(data["debug"]["reranker_used"])
                        self.assertEqual(data["grounding"]["status"], "grounded")


if __name__ == "__main__":
    unittest.main()
