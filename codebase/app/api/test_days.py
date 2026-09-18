"""Day catalogs and hard day filtering through the real offline pipeline."""

import copy
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import numpy as np
import pymupdf
from fastapi.testclient import TestClient

from app.api.main import app
from app.ingestion.ingest import ingest_pdfs
from app.qa.generator import AnswerGenerator
from app.qa.service import QAService
from app.retrieval.dense import DenseIndex
from app.retrieval.service import RetrievalService


class LearningDayIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.pdf_dir, self.index_dir = self.root / "pdf", self.root / "index"
        environment = patch.dict(os.environ, {"VISION_ENABLED": "false", "RERANK_ENABLED": "false",
            "NEIGHBOR_EXPANSION_ENABLED": "true", "NEIGHBOR_DISTANCE": "1", "NO_ANSWER_THRESHOLD": "",
            "EVIDENCE_TOP_K": "5", "MAX_EVIDENCE_PER_SLIDE": "2", "TOP_K": "5", "PDF_DIR": str(self.pdf_dir)})
        environment.start()
        self.addCleanup(environment.stop)
        for filename, passages in {
            "Day01/a.pdf": ["Shared concept: alpha matrix normalization.", "Alpha updates model parameters."],
            "Day01/b.pdf": ["Shared concept: beta convolution.", "Beta pooling reduces spatial features.", "Beta conclusions."],
            "Day02/c.pdf": ["Shared concept shared concept shared concept: unrelated day.", "Shared concept unrelated continuation."],
            "unknown.pdf": [""],
        }.items():
            path = self.pdf_dir / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            with pymupdf.open() as pdf:
                for text in passages:
                    page = pdf.new_page()
                    if text:
                        page.insert_text((40, 80), text)
                pdf.save(path)
        ingest_pdfs(self.pdf_dir, self.index_dir / "slides.json")
        previous = {name: getattr(app.state, name, None) for name in ("retrieval_service", "qa_service")}

        def restore():
            for name, value in previous.items():
                if value is None:
                    if hasattr(app.state, name):
                        delattr(app.state, name)
                else:
                    setattr(app.state, name, value)
        self.addCleanup(restore)
        self.retrieval = RetrievalService(self.index_dir, dense_enabled=False)
        app.state.retrieval_service = self.retrieval
        app.state.qa_service = QAService(generator=AnswerGenerator(api_key=""))
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_catalog_and_document_grouping_include_blank_unassigned_slides(self):
        result = self.client.get("/api/days").json()
        self.assertEqual([d["day_id"] for d in result["days"]], ["Day01", "Day02"])
        day = result["days"][0]
        self.assertEqual((day["document_count"], day["slide_count"]), (2, 5))
        self.assertEqual([d["filename"] for d in day["documents"]], ["Day01/a.pdf", "Day01/b.pdf"])
        self.assertEqual([d["total_pages"] for d in day["documents"]], [2, 3])
        self.assertEqual(result["unassigned_slide_count"], 1)
        self.assertEqual(result["unassigned_documents"][0]["searchable_slides"], 0)
        self.assertEqual(self.client.get("/api/days/D01").json(), day)

    def test_full_day_slides_paginate_without_omitting_a_document(self):
        slides = []
        for offset in (0, 2, 4):
            response = self.client.get("/api/days/day1/slides", params={"offset": offset, "limit": 2})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["total"], 5)
            slides.extend(response.json()["slides"])
        self.assertEqual([(s["filename"], s["page_number"]) for s in slides],
                         [("Day01/a.pdf", 1), ("Day01/a.pdf", 2), ("Day01/b.pdf", 1), ("Day01/b.pdf", 2), ("Day01/b.pdf", 3)])
        self.assertEqual(len({s["slide_id"] for s in slides}), 5)
        self.assertTrue(all(s["day_id"] == "Day01" for s in slides))
        self.assertEqual(self.client.get("/api/days/Day01/slides?offset=5").json()["slides"], [])

    def test_filtered_ask_citations_and_neighbors_never_leave_day(self):
        response = self.client.post("/api/ask", json={"question": "Shared concept", "day_id": "D01"})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertTrue(result["citations"])
        self.assertEqual(result["debug"]["day_filter"], "Day01")
        for source in result["citations"]:
            self.assertEqual((source["day_id"], source["day_number"], source["day_label"]), ("Day01", 1, "Day 01"))
            self.assertTrue(source["filename"].startswith("Day01/"))
            self.assertEqual(self.client.get(source["viewer_url"]).status_code, 200)
        retrieval = self.retrieval.retrieve("Shared concept", top_k=1, day_id="Day01")
        self.assertTrue(retrieval["context_slides"])
        self.assertTrue(all(s["day_id"] == "Day01" for s in retrieval["primary_slides"] + retrieval["context_slides"]))
        unfiltered = self.retrieval.retrieve("Shared concept", top_k=5)
        self.assertEqual({s["day_id"] for s in unfiltered["primary_slides"]}, {"Day01", "Day02"})
        result = self.client.post("/api/ask", json={"question": "Shared concept", "day_id": "Day02"}).json()
        self.assertTrue(result["citations"])
        self.assertTrue(all(c["day_id"] == "Day02" for c in result["citations"]))

    def test_unknown_and_invalid_days_fail_closed(self):
        for day, status in (("Day99", 404), ("Day0", 422), ("invalid", 422)):
            self.assertEqual(self.client.get("/api/days/" + day).status_code, status)
            self.assertEqual(self.client.post("/api/ask", json={"question": "Shared", "day_id": day}).status_code, status)
        self.assertEqual(self.retrieval.retrieve("Shared", day_id="Day99")["evidence"], [])
        for query in ("offset=-1", "limit=0", "limit=201"):
            self.assertEqual(self.client.get("/api/days/Day01/slides?" + query).status_code, 422)

    def test_legacy_index_derives_days_and_invalid_reload_preserves_catalog(self):
        path = self.index_dir / "slides.json"
        original = json.loads(path.read_text(encoding="utf-8"))
        legacy = [{k: v for k, v in s.items() if k not in {"day_id", "day_number", "day_label"}} for s in original]
        path.write_text(json.dumps(legacy), encoding="utf-8")
        catalog = self.retrieval.list_days()
        self.assertEqual(catalog["days"][0]["document_count"], 2)
        malformed = copy.deepcopy(original)
        malformed[1]["day_id"], malformed[1]["day_number"] = "Day02", 2
        path.write_text(json.dumps(malformed), encoding="utf-8")
        self.assertEqual(self.retrieval.list_days(), catalog)
        self.assertEqual(self.retrieval.get_day("D01")["slide_count"], 5)

    def test_dense_filters_before_top_k_and_handles_empty_candidate_set(self):
        self.retrieval._load()
        records = self.retrieval.slides + [dict(self.retrieval.slides[-1], slide_id=f"extra{i}") for i in range(25)]
        dense = DenseIndex(records, self.index_dir)
        scores = np.array([0.1, 0.2] + [0.9] * (len(records) - 2))
        dense.embeddings = np.zeros((len(records), 384))
        dense.embeddings[:, 0] = scores
        dense.embeddings[:, 1] = np.sqrt(1 - scores ** 2)

        class Model:
            def encode(self, texts, **kwargs):
                vector = np.zeros((1, 384))
                vector[:, 0] = 1
                return vector
        dense.model = Model()
        self.assertEqual(dense.search("query", limit=1)[0][0], 2)
        self.assertEqual(dense.search("query", limit=1, allowed_indices=[0, 1])[0][0], 1)
        self.assertEqual(dense.search("query", allowed_indices=[]), [])
        self.assertFalse(dense.failed)

    def test_hybrid_fusion_and_e5_evidence_remain_inside_requested_day(self):
        self.retrieval._load()
        dense = DenseIndex(self.retrieval.slides, self.index_dir)
        dense.embeddings = np.zeros((len(self.retrieval.slides), 384))
        dense.embeddings[:, 0] = [0.1 if s["day_id"] == "Day01" else 0.99 for s in self.retrieval.slides]
        dense.embeddings[:, 1] = np.sqrt(1 - dense.embeddings[:, 0] ** 2)

        class Model:
            def encode(self, texts, **kwargs):
                vectors = np.zeros((len(texts), 384))
                vectors[:, 0] = 1
                return vectors
        dense.model = Model()
        self.retrieval.dense = dense
        result = self.retrieval.retrieve("Shared concept", top_k=20, day_id="Day01")
        self.assertEqual(len(result["primary_slides"]), 5)
        self.assertEqual(result["debug"]["block_ranking_method"], "e5")
        self.assertFalse(result["debug"]["block_ranking_fallback"])
        self.assertTrue(all(s["day_id"] == "Day01" for s in result["primary_slides"] + result["context_slides"] + result["evidence"]))

    def test_multi_day_scope_normalizes_and_keeps_citations_in_scope(self):
        response = self.client.post("/api/ask", json={"question": "Shared concept", "scope": ["d1", "day 2", "Day01"]})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["debug"]["scope_filter"], ["Day01", "Day02"])
        self.assertEqual({c["day_id"] for c in result["citations"]}, {"Day01", "Day02"})
        scoped = self.retrieval.retrieve("Shared concept", top_k=20, scope=["D01"])
        self.assertTrue(all(s["day_id"] == "Day01" for s in scoped["primary_slides"] + scoped["context_slides"] + scoped["evidence"]))

    def test_scope_and_legacy_day_intersect_and_reject_conflicts(self):
        for endpoint, field in (("/api/ask", "question"), ("/api/mindmap/generate", "topic")):
            response = self.client.post(endpoint, json={field: "Shared concept", "day_id": "D01", "scope": ["D01", "D02"]})
            self.assertEqual(response.status_code, 200, response.text)
            result = response.json()
            sources = result["citations"] if field == "question" else [n for b in result["branches"] for n in b["nodes"]]
            self.assertTrue(sources)
            self.assertEqual({s["day_id"] for s in sources}, {"Day01"})
            conflict = self.client.post(endpoint, json={field: "Shared concept", "day_id": "D01", "scope": ["D02"]})
            self.assertEqual(conflict.status_code, 422, conflict.text)
        with self.assertRaises(ValueError):
            self.retrieval.retrieve("Shared", day_id="Day01", scope=["Day02"])

    def test_invalid_scope_fails_closed_for_qa_and_mindmap(self):
        for endpoint, field in (("/api/ask", "question"), ("/api/mindmap/generate", "topic")):
            for scope, status in ((["Day99"], 404), (["Day01", "Day99"], 404), (["nope"], 422), (["Day0"], 422), ([""], 422), ("Day01", 422)):
                with self.subTest(endpoint=endpoint, scope=scope):
                    self.assertEqual(self.client.post(endpoint, json={field: "Shared", "scope": scope}).status_code, status)
            self.assertEqual(self.client.post(endpoint, json={field: "Shared", "scope": []}).status_code, 200)

    def test_mindmap_day_alias_and_topic_sources_open_real_pages(self):
        overview = self.client.get("/api/mindmap?day=D01")
        self.assertEqual(overview.status_code, 200, overview.text)
        self.assertEqual(overview.json()["day"], "Day01")
        for node in [n for branch in overview.json()["branches"] for n in branch["nodes"]]:
            self.assertEqual(node["day_id"], "Day01")
            self.assertEqual(self.client.get(node["viewer_url"]).status_code, 200)
        topic = self.client.post("/api/mindmap/generate", json={"topic": "Alpha", "day_id": "D01"})
        self.assertEqual(topic.status_code, 200, topic.text)
        sources = [n for branch in topic.json()["branches"] for n in branch["nodes"]]
        self.assertTrue(sources)
        for node in sources:
            self.assertEqual(node["day_id"], "Day01")
            self.assertIn("alpha", node["quote"].lower())
            self.assertEqual(self.client.get(node["viewer_url"]).status_code, 200)
            self.assertEqual(self.client.get("/api/page", params={"file": node["filename"], "page": node["page_number"]}).status_code, 200)
        self.assertEqual(self.client.get("/api/mindmap?day=Day99").status_code, 404)
        self.assertEqual(self.client.get("/api/mindmap?day=invalid").status_code, 422)

    def test_busy_mindmap_returns_503_and_health_still_works(self):
        locked, release = threading.Event(), threading.Event()
        def hold():
            with self.retrieval._lock:
                locked.set()
                release.wait(5)
        thread = threading.Thread(target=hold)
        thread.start()
        self.assertTrue(locked.wait(1))
        try:
            with patch.dict(os.environ, {"REQUEST_TIMEOUT_SECONDS": "0.1"}):
                for method, endpoint, body in (("get", "/api/mindmap?day=Day01", None), ("post", "/api/mindmap/generate", {"topic": "Alpha"})):
                    started = time.monotonic()
                    response = self.client.request(method, endpoint, json=body)
                    self.assertEqual(response.status_code, 503, response.text)
                    self.assertLess(time.monotonic() - started, 1)
            self.assertEqual(self.client.get("/api/health").status_code, 200)
        finally:
            release.set()
            thread.join(1)

    def test_available_scopes_use_metadata_including_blank_day(self):
        path = self.index_dir / "slides.json"
        records = json.loads(path.read_text(encoding="utf-8"))
        records[-1].update(day_id="Day03", day_number=3, day_label="Day 03")
        # Metadata is authoritative even when the filename has no Day prefix.
        records[0]["filename"] = "nested/custom/alpha.pdf"
        path.write_text(json.dumps(records), encoding="utf-8")
        self.assertEqual(self.retrieval.available_scopes, ["Day01", "Day02", "Day03"])
        self.assertTrue(any(n["filename"] == "nested/custom/alpha.pdf" for n in self.retrieval.mindmap_nodes("D01")))
        self.assertEqual(self.client.get("/api/mindmap?day=Day03").json()["branches"], [])

    def test_day_range_intent_and_overview_work_without_model(self):
        path = self.pdf_dir / "Day03/d.pdf"
        path.parent.mkdir()
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text((40, 80), "Agent orchestration and tool calling.")
            pdf.save(path)
        ingest_pdfs(self.pdf_dir, self.index_dir / "slides.json")
        response = self.client.post("/api/mindmap/intent", json={"message": "tao mindmap từ day 1 đến day 3"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"day": None, "scope": ["Day01", "Day02", "Day03"], "topic": None})
        overview = self.client.post("/api/mindmap/overview", json={"scope": response.json()["scope"]})
        self.assertEqual(overview.status_code, 200, overview.text)
        branches = overview.json()["branches"]
        self.assertEqual([branch["label"] for branch in branches], ["Day 01", "Day 02", "Day 03"])
        for day, branch in zip(("Day01", "Day02", "Day03"), branches):
            self.assertTrue(branch["nodes"])
            for node in branch["nodes"]:
                self.assertEqual(node["day_id"], day)
                self.assertEqual(self.client.get(node["viewer_url"]).status_code, 200)

    def test_overview_rejects_empty_unknown_or_invalid_scope(self):
        for payload, status in (({}, 422), ({"scope": []}, 422), ({"scope": ["Day01", "Day99"]}, 404), ({"scope": ["wrong"]}, 422)):
            self.assertEqual(self.client.post("/api/mindmap/overview", json=payload).status_code, status)
        self.assertEqual(self.client.post("/api/mindmap/intent", json={"message": "mindmap day 3 đến day 1"}).status_code, 422)
