"""Real scoped index + orchestrator + HTTP/viewer, without paid API calls."""

import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

import pymupdf
from fastapi.testclient import TestClient

from app.agent.contracts import DocumentSelection
from app.agent.service import ChatAgent
from app.agent.tools import EvidenceStore
from app.api.main import app
from app.qa.generator import AnswerGenerator
from app.qa.service import QAService
from app.retrieval.query import extract_study_topic, normalize_topic
from app.retrieval.service import RetrievalService

QUESTION = "tạo mindmap các file tài liệu tôi cần học tên gì nằm ở day nào để tôi hiểu về tranformers"


class Reviewer:
    available = True

    def __init__(self, callback=None):
        self.calls = []
        self.callback = callback

    def generate_json(self, prompt, **kwargs):
        data = json.loads(prompt)
        self.calls.append((data, kwargs))
        if self.callback:
            return self.callback(data, kwargs)
        if kwargs["name"] == "lecture_task_plan":
            return {"task": "topic_map", "output_format": "mindmap", "topic": "Transformer", "scope": None}
        return self.selection(data)

    @staticmethod
    def selection(data):
        documents = []
        for metadata in data["CATALOG"]:
            name = metadata["filename"]
            if "foundation" not in name and "architecture" not in name:
                continue
            sources = [source for source in data["EVIDENCE"]
                       if source["document_id"] == metadata["document_id"]]
            documents.append({"document_id": metadata["document_id"],
                              "evidence_ids": [source["evidence_id"] for source in sources[:2]],
                              "role": "core", "reason": "Giải thích cơ chế self-attention trong Transformer."})
        return {"documents": documents, "missing_queries": []}

    def generate(self, prompt, *, instructions=None):
        return "Transformer dùng self-attention. [E1]"


class AgentIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.pdf_dir = self.root / "pdf"
        index = self.root / "index"
        index.mkdir()
        environment = patch.dict(os.environ, {
            "OPENAI_API_KEY": "", "RERANK_ENABLED": "false", "VISION_ENABLED": "false",
            "NEIGHBOR_EXPANSION_ENABLED": "true", "NO_ANSWER_THRESHOLD": "", "TOP_K": "5",
            "PDF_DIR": str(self.pdf_dir), "AGENT_MAX_DOCUMENTS": "8",
        })
        environment.start()
        self.addCleanup(environment.stop)
        self.records = []
        for filename, pages in {
            "Day01/foundation & intro.pdf": [
                "Transformers use self-attention to relate tokens to each other.",
                "Transformer self-attention computes queries, keys and values from token embeddings.",
            ],
            "Day02/architecture.pdf": [
                "Transformer architecture combines self-attention with feed-forward layers.",
                "Transformer attention computes normalized query-key scores before summing values.",
            ],
            "Day03/mention.pdf": ["Model list: Transformers, CNN, RNN. Today's lesson covers image convolution."],
            "Day03/unrelated.pdf": ["Convolution applies shared spatial kernels to images."],
            "unknown.pdf": ["Transformer self-attention uses token relationships."],
        }.items():
            path = self.pdf_dir / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            with pymupdf.open() as pdf:
                for page_number, text in enumerate(pages, 1):
                    page = pdf.new_page()
                    page.insert_text((40, 80), text)
                    self.records.append({"slide_id": f"{filename}_{page_number}", "filename": filename,
                                         "page_number": page_number, "text": text,
                                         "blocks": [{"text": text, "bbox": [0.1, 0.1, 0.9, 0.3]}]})
                pdf.save(path)
        (index / "slides.json").write_text(json.dumps(self.records), encoding="utf-8")
        self.retrieval = RetrievalService(index, dense_enabled=False)
        self.generator = Reviewer()
        self.qa = QAService(generator=self.generator)
        previous = {key: getattr(app.state, key, None) for key in ("retrieval_service", "qa_service")}

        def restore():
            for key, value in previous.items():
                if value is None:
                    if hasattr(app.state, key):
                        delattr(app.state, key)
                else:
                    setattr(app.state, key, value)
        self.addCleanup(restore)
        app.state.retrieval_service = self.retrieval
        app.state.qa_service = self.qa
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def chat(self, question=QUESTION, **extra):
        result = self.client.post("/api/chat", json={"question": question, **extra})
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()

    def test_compound_request_returns_exact_documents_days_and_working_sources(self):
        result = self.chat()
        self.assertEqual((result["task"], result["output_format"], result["status"]),
                         ("study_materials", "mindmap", "completed"))
        self.assertEqual({document["filename"] for document in result["documents"]},
                         {"Day01/foundation & intro.pdf", "Day02/architecture.pdf"})
        self.assertEqual({branch["label"] for branch in result["branches"]}, {"Day 01", "Day 02"})
        self.assertIn("tranformers → transformers", result["answer"])
        self.assertEqual(result["debug"]["agent"]["original_question"], QUESTION)
        for document in result["documents"]:
            node = next(node for branch in result["branches"] for node in branch["nodes"]
                        if node["document_id"] == document["document_id"])
            self.assertEqual(node["label"], document["filename"])
            self.assertTrue(document["sources"])
            for source in document["sources"]:
                raw = next(raw for raw in self.records if raw["slide_id"] == source["slide_id"])
                self.assertIn(source["quote"], raw["text"])
                self.assertEqual(source["filename"], document["filename"])
                self.assertEqual(source["day_id"], document["day_id"])
                parameters = parse_qs(urlsplit(source["viewer_url"]).query)
                self.assertEqual(parameters["file"], [document["filename"]])
                self.assertEqual(parameters["evidence"], [source["evidence_id"]])
                self.assertEqual(self.client.get(source["viewer_url"]).status_code, 200)
                image = self.client.get("/api/page", params={"file": source["filename"], "page": source["page_number"]})
                self.assertEqual(image.status_code, 200)
                self.assertTrue(image.content.startswith(b"\x89PNG"))
        self.assertEqual(len(self.generator.calls), 1)

    def test_text_document_request_uses_same_grounded_discovery(self):
        result = self.chat("Tôi muốn học về kiến thức Transformers trong khóa học, tài liệu nào nằm ở ngày nào?")
        self.assertEqual((result["task"], result["output_format"]), ("study_materials", "text"))
        self.assertEqual(len(result["documents"]), 2)
        self.assertEqual(result["branches"], [])

    def test_scope_filters_all_tools_and_citations(self):
        result = self.chat(scope=["D01"])
        self.assertEqual(len(result["documents"]), 1)
        self.assertTrue(all(source["day_id"] == "Day01" for source in result["citations"]))
        result = self.chat(QUESTION + " từ day 1 đến day 2", scope=["Day01", "Day02", "Day03"])
        self.assertEqual(result["debug"]["agent"]["scope_filter"], ["Day01", "Day02"])

    def test_invalid_unknown_and_outside_scope_days_fail_closed(self):
        for extra_question, payload, status in (
            (" day 99", {}, 404), (" day 0", {}, 422),
            (" từ day 3 đến day 1", {}, 422), (" day 2", {"scope": ["Day01"]}, 422),
            ("", {"scope": ["Day99"]}, 404),
        ):
            response = self.client.post("/api/chat", json={"question": QUESTION + extra_question, **payload})
            self.assertEqual(response.status_code, status, response.text)

    def test_unknown_topic_respects_semantic_abstention(self):
        self.generator.callback = lambda data, options: {"documents": [], "missing_queries": []}
        result = self.chat("tạo mindmap tài liệu tôi cần học về qwertyzxc")
        self.assertEqual(result["status"], "no_evidence")
        self.assertEqual(result["documents"], [])
        self.assertEqual(result["branches"], [])
        self.assertEqual(result["citations"], [])

    def test_rejects_fake_and_cross_document_sources_but_keeps_valid_selection(self):
        def review(data, options):
            result = Reviewer.selection(data)
            result["documents"][1]["evidence_ids"] = [result["documents"][0]["evidence_ids"][0]]
            result["documents"].append({"document_id": "fake", "evidence_ids": ["E999"],
                                        "role": "core", "reason": "Unsupported claim"})
            return result
        self.generator.callback = review
        result = self.chat()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["documents"]), 1)
        self.assertEqual(result["debug"]["agent"]["invalid_selections_removed"], 2)
        self.assertNotIn("E999", result["answer"])

    def test_bounded_refinement_assigns_unique_request_source_ids(self):
        def review(data, options):
            result = Reviewer.selection(data)
            if not data["LAST_ROUND"]:
                result["missing_queries"] = ["Transformer attention query key values"]
            return result
        self.generator.callback = review
        result = self.chat()
        self.assertEqual(result["debug"]["agent"]["retrieval_rounds"], 2)
        self.assertEqual(len(self.generator.calls), 2)
        all_sources = self.generator.calls[-1][0]["EVIDENCE"]
        ids = [source["evidence_id"] for source in all_sources]
        self.assertEqual(len(ids), len(set(ids)))
        first = {source["evidence_id"]: source for source in self.generator.calls[0][0]["EVIDENCE"]}
        for source in all_sources:
            if source["evidence_id"] in first:
                self.assertEqual(source, first[source["evidence_id"]])

    def test_refinement_timeout_preserves_already_verified_documents(self):
        def review(data, options):
            result = Reviewer.selection(data)
            result["missing_queries"] = ["Transformer attention query key values"]
            return result
        self.generator.callback = review
        original = self.retrieval.search_documents
        count = 0

        def search(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                raise TimeoutError("timed out")
            return original(*args, **kwargs)
        with patch.object(self.retrieval, "search_documents", side_effect=search):
            result = self.chat()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["documents"]), 2)

    def test_initial_timeout_is_not_reported_as_missing_content(self):
        with patch.object(self.retrieval, "search_documents", side_effect=TimeoutError()):
            result = self.chat()
        self.assertEqual(result["status"], "retrieval_timeout")
        self.assertIn("chưa thể kết luận", result["answer"])

    def test_unavailable_model_only_exposes_direct_mentions(self):
        app.state.qa_service = QAService(generator=AnswerGenerator(api_key=""))
        result = self.chat()
        self.assertEqual(result["status"], "partial")
        self.assertFalse(result["grounding"]["document_review_completed"])
        self.assertNotIn("Day03/unrelated.pdf", [document["filename"] for document in result["documents"]])
        self.assertTrue(all("chưa thẩm định" in document["reason"] for document in result["documents"]))
        unknown = self.chat("mindmap tài liệu tôi cần học về qwertyzxc")
        self.assertEqual(unknown["status"], "no_evidence")
        self.assertEqual(unknown["documents"], [])

    def test_malformed_review_is_partial_without_fabricating_advice(self):
        self.generator.callback = lambda data, options: {"invented": "wrong schema"}
        result = self.chat()
        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["debug"]["agent"]["review_fallback"])
        self.assertTrue(all("chưa thẩm định" in document["reason"] for document in result["documents"]))

    def test_followup_uses_previous_topic_and_document_ids(self):
        first = self.chat("Tôi muốn học về Transformers, cần học tài liệu nào?")
        second = self.chat("tạo mindmap các tài liệu đó", context=first["context"])
        self.assertEqual(second["task"], "study_materials")
        self.assertEqual(second["context"]["topic"], "Transformers")
        self.assertEqual({document["document_id"] for document in second["documents"]},
                         set(first["context"]["document_ids"]))

    def test_normal_qa_and_topic_and_day_mindmaps_still_work(self):
        result = self.chat("Transformer là gì?", scope=["Day01"])
        self.assertEqual((result["task"], result["output_format"]), ("answer", "text"))
        self.assertTrue(result["citations"])
        topic_map = self.chat("tạo mindmap về Transformer day 1")
        self.assertEqual(topic_map["task"], "topic_map")
        self.assertTrue(topic_map["branches"])
        overview = self.chat("tạo mindmap từ day 1 đến day 2")
        self.assertEqual(overview["task"], "day_summary")
        self.assertEqual({branch["label"] for branch in overview["branches"]}, {"Day 01", "Day 02"})

    def test_discovery_can_return_more_than_legacy_five_evidence_limit(self):
        result = self.retrieval.search_documents("transformer convolution", limit=8)
        self.assertEqual(len(result["slides"]), 5)
        # The explicit contract also works with a per-request evidence budget.
        with patch.dict(os.environ, {"EVIDENCE_TOP_K": "1"}):
            result = self.retrieval.search_documents("transformer convolution", limit=8)
        self.assertGreater(len(result["evidence"]), 1)

    def test_empty_request_and_oversized_context_are_rejected(self):
        for payload in ({"question": " "}, {"question": "x" * 4001},
                        {"question": QUESTION, "context": {"task": "study_materials", "document_ids": ["x"] * 13}}):
            self.assertEqual(self.client.post("/api/chat", json=payload).status_code, 422)

    def test_provider_failure_is_not_a_claim_that_content_is_missing(self):
        def unavailable(data, options):
            raise RuntimeError("provider unavailable")
        self.generator.callback = unavailable
        result = self.chat()
        self.assertEqual(result["status"], "partial")
        self.assertTrue(all(document["role"] == "candidate" for document in result["documents"]))
        self.assertFalse(result["grounding"]["document_review_completed"])
        self.assertNotIn("Day03/unrelated.pdf", [document["filename"] for document in result["documents"]])

    def test_bad_explicit_day_does_not_spend_a_planner_call(self):
        response = self.client.post("/api/chat", json={"question": "tạo mindmap về Transformer day 99"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.generator.calls, [])

    def test_topic_followup_retains_the_previous_subject(self):
        result = self.chat("tạo mindmap chủ đề đó", context={"task": "topic_map", "topic": "Transformer"})
        self.assertEqual((result["task"], result["context"]["topic"]), ("topic_map", "Transformer"))
        self.assertTrue(result["branches"])


class NormalizationAndGeneratorTests(unittest.TestCase):
    def test_shared_normalization_and_ambiguous_names(self):
        self.assertEqual(normalize_topic("tranformers", {"transformers": 3, "transformer": 3}),
                         ("transformers", ["transformer"], {"tranformers": "transformers"}))
        self.assertEqual(normalize_topic("qwertyzxc", {"transformers": 3})[0], "qwertyzxc")
        self.assertEqual(normalize_topic("abcdefghij", {"abcdefghix": 3, "abcdefghiy": 3})[0], "abcdefghij")
        self.assertEqual(extract_study_topic(QUESTION), "tranformers")
        self.assertEqual(extract_study_topic("Tôi muốn học về kiến thức A trong khóa học, tài liệu nào?"), "A")

    def test_strict_json_adapter_keeps_model_and_disables_storage(self):
        response = SimpleNamespace(status="completed", output_text='{"value": "ok"}')
        create = Mock(return_value=response)
        generator = AnswerGenerator(client=SimpleNamespace(responses=SimpleNamespace(create=create)), model="configured-model")
        result = generator.generate_json("request", instructions="rules", schema={"type": "object"}, name="test", timeout=8)
        self.assertEqual(result, {"value": "ok"})
        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs["model"], "configured-model")
        self.assertTrue(kwargs["text"]["format"]["strict"])
        self.assertFalse(kwargs["store"])
        self.assertLessEqual(kwargs["timeout"], 8)

    def test_store_rejects_wrong_metadata_and_reuses_ids_across_rounds(self):
        metadata = {"document_id": "doc", "filename": "Day01/a.pdf", "day_id": "Day01", "total_pages": 3}
        store = EvidenceStore({"doc": metadata}, ["Day01"])
        raw = {"document_id": "doc", "filename": "Day01/a.pdf", "page_number": 1,
               "slide_id": "s1", "quote": "Transformer attention", "evidence_id": "E1"}
        self.assertEqual(store.add([raw]), ["E1"])
        self.assertEqual(store.add([raw]), ["E1"])
        self.assertEqual(store.add([{**raw, "page_number": 2, "slide_id": "s2"}]), ["E2"])
        self.assertEqual(store.add([{**raw, "filename": "Day02/fake.pdf"}]), [])
        self.assertEqual(store.add([{**raw, "page_number": 4}]), [])
        self.assertEqual(len(store.sources), 2)


if __name__ == "__main__":
    unittest.main()
