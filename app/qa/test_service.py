"""Run with python -m unittest app.qa.test_service -v (no API calls)."""

import copy
import json
import unittest
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from .generator import AnswerGenerator
from .prompts import INSUFFICIENT_EVIDENCE, MINDMAP_SYSTEM_PROMPT, ORGANIZE_SYSTEM_PROMPT, SYSTEM_PROMPT
from .service import QAService, prepare_evidence


def mindmap_node(**updates):
    item = {
        "label": "Retrieval cơ bản", "filename": "Day05/gv.pdf", "page_number": 3,
        "bbox": [0.1, 0.1, 0.5, 0.2], "slide_id": "doc_p0003",
        "viewer_url": "/viewer?file=Day05%2Fgv.pdf&page=3",
    }
    item.update(updates)
    return item


def source(**updates):
    item = {
        "evidence_id": "old_id",
        "slide_id": "doc_p0007",
        "block_id": "doc_p0007_b000",
        "filename": "Bài giảng & học.pdf",
        "page_number": 7,
        "quote": "  Gradient descent cập nhật trọng số theo gradient.\n",
        "bbox": [0.1, 0.2, 0.8, 0.4],
        "viewer_url": "/viewer?file=old.pdf&page=1&evidence=old_id&zoom=2",
    }
    item.update(updates)
    return item


class FakeGenerator:
    available = True

    def __init__(self, output):
        self.output = output
        self.prompt = None
        self.instructions = None

    def generate(self, prompt, *, instructions=None):
        self.prompt = prompt
        self.instructions = instructions
        if isinstance(self.output, Exception):
            raise self.output
        return self.output


class QATests(unittest.TestCase):
    def test_missing_key_extractive_preserves_source(self):
        evidence = [source()]
        original = copy.deepcopy(evidence)
        result = QAService(generator=AnswerGenerator(api_key="")).answer("Gradient là gì?", evidence)
        self.assertIn("[E1]", result["answer"])
        self.assertEqual(result["citations"][0]["quote"], evidence[0]["quote"])
        self.assertEqual(evidence, original)
        query = parse_qs(urlsplit(result["citations"][0]["viewer_url"]).query)
        self.assertEqual(query, {"file": [evidence[0]["filename"]], "page": ["7"], "evidence": ["E1"], "zoom": ["2"]})

    def test_empty_or_invalid_sources_abstain_without_model(self):
        generator = FakeGenerator("must not be used")
        service = QAService(generator=generator)
        for evidence in ([], [source(quote=" ")], [source(page_number=0)], [source(filename="")]):
            self.assertEqual(service.answer("Câu hỏi", evidence), {"answer": INSUFFICIENT_EVIDENCE, "citations": []})
        self.assertIsNone(generator.prompt)

    def test_blank_question_abstains(self):
        self.assertEqual(QAService().answer(" ", [source()])["citations"], [])

    def test_deterministic_ids_and_deduplication(self):
        evidence = [source(), source(), source(block_id="b2", quote="Đoạn hai")]
        self.assertEqual([s["evidence_id"] for s in prepare_evidence(evidence)], ["E1", "E2"])

    def test_model_citation_mapping_order_and_invalid_ids(self):
        generator = FakeGenerator("Đoạn hai [E2]. Đoạn một [E1]. [E999] [E0] [e1]")
        result = QAService(generator=generator).answer("Câu hỏi", [source(), source(block_id="b2", quote="Đoạn hai")])
        self.assertEqual([s["evidence_id"] for s in result["citations"]], ["E2", "E1"])
        for invalid in ("[E999]", "[E0]", "[e1]"):
            self.assertNotIn(invalid, result["answer"])
        self.assertNotIn("viewer_url", generator.prompt)
        self.assertIn("EVIDENCE:", generator.prompt)

    def test_no_valid_citations_falls_back(self):
        for output in ("Kiến thức không có nguồn", "Sai [E999]", ""):
            result = QAService(generator=FakeGenerator(output)).answer("Câu hỏi", [source()])
            self.assertIn(source()["quote"], result["answer"])
            self.assertEqual(len(result["citations"]), 1)

    def test_api_failure_falls_back(self):
        result = QAService(generator=FakeGenerator(TimeoutError())).answer("Câu hỏi", [source()])
        self.assertIn("[E1]", result["answer"])

    def test_model_abstention(self):
        result = QAService(generator=FakeGenerator(INSUFFICIENT_EVIDENCE)).answer("Câu hỏi", [source()])
        self.assertEqual(result, {"answer": INSUFFICIENT_EVIDENCE, "citations": []})

    def test_bad_bbox_dropped_and_text_alias_supported(self):
        for bbox in ([1, 2, 3, 4], [0, 0, float("nan"), 1], [0.9, 0, 0.1, 1]):
            self.assertIsNone(prepare_evidence([source(bbox=bbox)])[0]["bbox"])
        item = source()
        item["text"] = item.pop("quote")
        self.assertEqual(prepare_evidence([item])[0]["quote"], item["text"])

    def test_extractive_limits_to_three(self):
        evidence = [source(block_id=str(i), quote=f"Đoạn {i}") for i in range(5)]
        result = QAService(generator=AnswerGenerator(api_key="")).answer("Câu hỏi", evidence)
        self.assertEqual(len(result["citations"]), 3)

    def test_openai_adapter_request(self):
        captured = {}
        def create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_text="Câu trả lời [E1]", status="completed")
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        generator = AnswerGenerator(client=client, model="configured-model")
        self.assertEqual(generator.generate("evidence-only-input"), "Câu trả lời [E1]")
        self.assertEqual(captured["model"], "configured-model")
        self.assertEqual(captured["instructions"], SYSTEM_PROMPT)
        self.assertEqual(captured["input"], "evidence-only-input")
        self.assertFalse(captured["store"])
        self.assertNotIn("tools", captured)

    def test_openai_adapter_accepts_custom_instructions(self):
        captured = {}
        def create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_text="{}", status="completed")
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        generator = AnswerGenerator(client=client, model="configured-model")
        generator.generate("input", instructions="custom rules")
        self.assertEqual(captured["instructions"], "custom rules")

    def test_mindmap_without_model_returns_extractive_branch(self):
        result = QAService(generator=AnswerGenerator(api_key="")).mindmap("RAG", [source()])
        self.assertEqual(result["title"], "RAG")
        self.assertEqual(len(result["branches"]), 1)
        node = result["branches"][0]["nodes"][0]
        self.assertIn(source()["quote"][:40], node["label"])
        self.assertEqual(node["bbox"], source()["bbox"])

    def test_mindmap_empty_evidence_returns_no_branches(self):
        generator = FakeGenerator("must not be used")
        result = QAService(generator=generator).mindmap("RAG", [])
        self.assertEqual(result, {"title": "RAG", "branches": []})
        self.assertIsNone(generator.prompt)

    def test_mindmap_parses_json_and_drops_invalid_evidence_ids(self):
        evidence = [source(), source(block_id="b2", quote="Đoạn hai")]
        generated = json.dumps({
            "branches": [
                {"label": "Truy xuất", "children": [
                    {"label": "Ý một", "evidence_id": "E1"},
                    {"label": "Ý bịa", "evidence_id": "E999"},
                ]},
                {"label": "Rỗng", "children": [{"label": "x", "evidence_id": "E404"}]},
                {"label": "Sinh câu trả lời", "children": [{"label": "Ý hai", "evidence_id": "E2"}]},
            ]
        })
        generator = FakeGenerator(generated)
        result = QAService(generator=generator).mindmap("RAG", evidence)
        self.assertEqual(generator.instructions, MINDMAP_SYSTEM_PROMPT)
        self.assertEqual([b["label"] for b in result["branches"]], ["Truy xuất", "Sinh câu trả lời"])
        self.assertEqual(len(result["branches"][0]["nodes"]), 1)
        self.assertEqual(result["branches"][0]["nodes"][0]["filename"], evidence[0]["filename"])
        self.assertEqual(result["branches"][0]["nodes"][0]["bbox"], evidence[0]["bbox"])

    def test_mindmap_falls_back_on_invalid_json_or_error(self):
        for output in ("not json", "{}", json.dumps({"branches": "nope"})):
            result = QAService(generator=FakeGenerator(output)).mindmap("RAG", [source()])
            self.assertEqual(len(result["branches"]), 1)
        result = QAService(generator=FakeGenerator(TimeoutError())).mindmap("RAG", [source()])
        self.assertEqual(len(result["branches"]), 1)

    def test_organize_mindmap_groups_by_index_and_drops_unused(self):
        nodes = [mindmap_node(label=f"Slide {i}", page_number=i) for i in range(4)]
        generated = json.dumps({
            "branches": [
                {"label": "Nhóm A", "indices": [0, 2]},
                {"label": "Trùng/bịa", "indices": [2, 99, "x"]},  # 2 already used, 99 & "x" invalid
            ]
        })
        generator = FakeGenerator(generated)
        branches = QAService(generator=generator).organize_mindmap("Day05", nodes)
        self.assertEqual(generator.instructions, ORGANIZE_SYSTEM_PROMPT)
        self.assertEqual(branches[0], {"label": "Nhóm A", "nodes": [nodes[0], nodes[2]]})
        # This is a representative overview, not a full index: the whole
        # "Trùng/bịa" branch had no valid new index so it's dropped, and
        # nodes 1 and 3 (never assigned to any branch) are simply left out
        # rather than forced into a catch-all.
        self.assertEqual([b["label"] for b in branches], ["Nhóm A"])

    def test_organize_mindmap_caps_nodes_per_branch(self):
        nodes = [mindmap_node(label=f"Slide {i}", page_number=i) for i in range(10)]
        generated = json.dumps({"branches": [{"label": "Nhóm A", "indices": list(range(10))}]})
        branches = QAService(generator=FakeGenerator(generated)).organize_mindmap("Day05", nodes)
        self.assertEqual(len(branches[0]["nodes"]), 6)

    def test_organize_mindmap_returns_none_without_model_or_nodes(self):
        self.assertIsNone(QAService(generator=AnswerGenerator(api_key="")).organize_mindmap("Day05", [mindmap_node()]))
        self.assertIsNone(QAService(generator=FakeGenerator("must not be used")).organize_mindmap("Day05", []))

    def test_organize_mindmap_falls_back_on_invalid_json_or_error(self):
        nodes = [mindmap_node()]
        for output in ("not json", "{}", json.dumps({"branches": "nope"})):
            self.assertIsNone(QAService(generator=FakeGenerator(output)).organize_mindmap("Day05", nodes))
        self.assertIsNone(QAService(generator=FakeGenerator(TimeoutError())).organize_mindmap("Day05", nodes))


if __name__ == "__main__":
    unittest.main()
