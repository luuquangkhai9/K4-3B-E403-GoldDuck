"""Run with python -m unittest app.qa.test_service -v (no API calls)."""

import copy
import os
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from .generator import AnswerGenerator
from .prompts import (
    INSUFFICIENT_EVIDENCE,
    INTENT_SYSTEM_PROMPT,
    MINDMAP_SYSTEM_PROMPT,
    ORGANIZE_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
)
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
    def setUp(self):
        environment = patch.dict(os.environ, {
            "NO_ANSWER_ENABLED": "true", "NO_ANSWER_THRESHOLD": "",
            "CITATION_VALIDATION_ENABLED": "true", "OPENAI_API_KEY": "",
        })
        environment.start()
        self.addCleanup(environment.stop)

    def test_off_switches_accept_whitespace(self):
        with patch.dict(os.environ, {"NO_ANSWER_ENABLED": " off ", "CITATION_VALIDATION_ENABLED": " OFF "}):
            service = QAService(generator=AnswerGenerator(api_key=""))
            self.assertFalse(service.no_answer_enabled)
            self.assertFalse(service.citation_validation_enabled)

    def test_missing_key_extractive_preserves_source(self):
        evidence = [source()]
        original = copy.deepcopy(evidence)
        result = QAService(generator=AnswerGenerator(api_key="")).answer("Gradient là gì?", evidence)
        self.assertIn("[E1]", result["answer"])
        self.assertEqual(result["citations"][0]["quote"], evidence[0]["quote"])
        self.assertEqual(evidence, original)
        query = parse_qs(urlsplit(result["citations"][0]["viewer_url"]).query)
        self.assertEqual(query, {"file": [evidence[0]["filename"]], "page": ["7"], "evidence": ["E1"], "zoom": ["2"], "bbox": ["0.1,0.2,0.8,0.4"]})

    def test_empty_or_invalid_sources_abstain_without_model(self):
        generator = FakeGenerator("must not be used")
        service = QAService(generator=generator)
        for evidence in ([], [source(quote=" ")], [source(page_number=0)], [source(filename="")]):
            result = service.answer("Câu hỏi", evidence)
            self.assertEqual(result["answer"], INSUFFICIENT_EVIDENCE)
            self.assertEqual(result["citations"], [])
            self.assertTrue(result["grounding"]["no_answer"])
        self.assertIsNone(generator.prompt)

    def test_blank_question_abstains(self):
        self.assertEqual(QAService().answer(" ", [source()])["citations"], [])

    def test_deterministic_ids_and_deduplication(self):
        evidence = [source(), source(), source(block_id="b2", quote="Đoạn hai")]
        self.assertEqual([s["evidence_id"] for s in prepare_evidence(evidence)], ["E1", "E2"])

    def test_model_citation_mapping_order_and_invalid_ids(self):
        generator = FakeGenerator("Đoạn hai [E2]. Đoạn một [E1]. Bổ sung [E2]. [E999] [E0] [e1]")
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

    def test_extractive_does_not_expose_source_citation_tokens(self):
        item = source(quote="Source includes [E999] and [E2].")
        result = QAService(generator=AnswerGenerator(api_key="")).answer("Question", [item])
        self.assertNotIn("[E999]", result["answer"])
        self.assertNotIn("[E2]", result["answer"])
        self.assertEqual(result["citations"][0]["quote"], item["quote"])

    def test_model_abstention(self):
        result = QAService(generator=FakeGenerator(INSUFFICIENT_EVIDENCE)).answer("Câu hỏi", [source()])
        self.assertEqual(result["answer"], INSUFFICIENT_EVIDENCE)
        self.assertEqual(result["citations"], [])
        self.assertEqual(result["grounding"]["status"], "insufficient_evidence")

    def test_regeneration_is_limited_and_can_repair_citations(self):
        generator = FakeGenerator("")
        outputs = iter(["Unsupported [E99]", "Supported [E1]"])
        calls = []
        def generate(prompt):
            calls.append(prompt)
            return next(outputs)
        generator.generate = generate
        result = QAService(generator=generator).answer("Question", [source()])
        self.assertEqual(result["answer"], "Supported [E1]")
        self.assertEqual(len(calls), 2)
        self.assertTrue(result["grounding"]["regenerated"])
        self.assertEqual(result["grounding"]["invalid_citations_removed"], ["E99"])
        generator.generate = lambda prompt: calls.append(prompt) or "No citations"
        calls.clear()
        result = QAService(generator=generator).answer("Question", [source()])
        self.assertEqual(len(calls), 2)
        self.assertTrue(result["grounding"]["extractive_fallback"])

    def test_low_score_abstains_without_api_and_v1_scores_optional(self):
        with patch.dict(os.environ, {"NO_ANSWER_ENABLED": "true", "NO_ANSWER_THRESHOLD": "0.5"}):
            generator = FakeGenerator("Supported [E1]")
            service = QAService(generator=generator)
            result = service.answer("Question", [source(block_score=0.2)])
            self.assertTrue(result["grounding"]["no_answer"])
            self.assertIsNone(generator.prompt)
            self.assertFalse(service.answer("Question", [source()])["grounding"]["no_answer"])
            self.assertFalse(service.answer("Question", [source(block_score=0.5)])["grounding"]["no_answer"])

    def test_primary_preference_and_v2_metadata(self):
        evidence = [source(source_role="neighbor", block_score=0.7), source(block_id="primary", source_role="primary", block_score=0.8)]
        result = QAService(generator=AnswerGenerator(api_key="")).answer("Question", evidence)
        self.assertEqual(result["citations"][0]["evidence_id"], "E2")
        self.assertEqual(result["citations"][0]["block_score"], 0.8)
        generator = FakeGenerator("Supported [E2]")
        QAService(generator=generator).answer("Question", evidence)
        self.assertIn('"source_role": "neighbor"', generator.prompt)

    def test_v2_disabled_still_removes_fabricated_ids_without_retry(self):
        with patch.dict(os.environ, {"CITATION_VALIDATION_ENABLED": "false", "NO_ANSWER_ENABLED": "false", "NO_ANSWER_THRESHOLD": "0.9"}):
            result = QAService(generator=FakeGenerator("Supported [E1] [E999] [E888]")).answer("Question", [source(block_score=0.1)])
        self.assertEqual(result["grounding"]["used_evidence_ids"], ["E1"])
        self.assertFalse(result["grounding"]["regenerated"])
        self.assertNotIn("[E999]", result["answer"])

    def test_invalid_citations_dominate_then_api_failure(self):
        generator = FakeGenerator("")
        outputs = iter(["Claim [E1] [E999] [E888]", TimeoutError()])
        def generate(prompt):
            output = next(outputs)
            if isinstance(output, Exception):
                raise output
            return output
        generator.generate = generate
        result = QAService(generator=generator).answer("Question", [source()])
        self.assertTrue(result["grounding"]["extractive_fallback"])
        self.assertTrue(result["grounding"]["regenerated"])
        self.assertNotIn("[E999]", result["answer"])

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

    def test_source_link_uses_validated_bbox(self):
        for bbox in ([0.1, 0.2, 0.8, 0.4], [0.1, 0.2, 0.1, 0.4], None):
            with self.subTest(bbox=bbox):
                item = prepare_evidence([source(bbox=bbox, viewer_url="/viewer?bbox=0,0,1,1&zoom=2")])[0]
                query = parse_qs(urlsplit(item["viewer_url"]).query)
                if item["bbox"]:
                    self.assertEqual([float(v) for v in query["bbox"][0].split(",")], item["bbox"])
                else:
                    self.assertNotIn("bbox", query)
                self.assertEqual(query["zoom"], ["2"])

    def test_malformed_metadata_does_not_crash(self):
        self.assertEqual(prepare_evidence([source(block_id=[]), source(block_id={})]), [])
        item = prepare_evidence([source(viewer_url="http://[invalid")])[0]
        self.assertTrue(item["viewer_url"].startswith("/viewer?"))

    def test_bbox_overflow_and_zero_area_are_dropped(self):
        for bbox in ([0, 0, 10 ** 1000, 1], [0.1, 0.2, 0.1, 0.4]):
            self.assertIsNone(prepare_evidence([source(bbox=bbox)])[0]["bbox"])

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

    def test_openai_adapter_omits_temperature_unless_explicitly_set(self):
        # Reasoning-tier models (the default gpt-5.6 included) reject an
        # explicit temperature outright ("Unsupported parameter") — omitting
        # it by default avoids turning every call into a 400.
        captured = {}
        def create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_text="{}", status="completed")
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        AnswerGenerator(client=client).generate("input")
        self.assertNotIn("temperature", captured)
        captured.clear()
        AnswerGenerator(client=client, temperature=0.0).generate("input")
        self.assertEqual(captured["temperature"], 0.0)

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

    def test_extract_mindmap_intent_returns_validated_day_and_topic(self):
        generator = FakeGenerator(json.dumps({"day": "Day07", "topic": "transformer"}))
        result = QAService(generator=generator).extract_mindmap_intent(
            "cho tôi xem mindmap của buổi học số 7 về transformer", ["Day01", "Day07"]
        )
        self.assertEqual(generator.instructions, INTENT_SYSTEM_PROMPT)
        self.assertEqual(result, {"day": "Day07", "topic": "transformer"})

    def test_extract_mindmap_intent_rejects_day_not_in_available_list(self):
        generator = FakeGenerator(json.dumps({"day": "Day99", "topic": "RAG"}))
        result = QAService(generator=generator).extract_mindmap_intent("...", ["Day01", "Day07"])
        self.assertEqual(result, {"day": None, "topic": "RAG"})

    def test_extract_mindmap_intent_returns_none_when_unusable(self):
        for output in ("not json", json.dumps({"day": None, "topic": None}), json.dumps({"day": None, "topic": "  "})):
            result = QAService(generator=FakeGenerator(output)).extract_mindmap_intent("...", ["Day01"])
            self.assertIsNone(result)
        self.assertIsNone(QAService(generator=AnswerGenerator(api_key="")).extract_mindmap_intent("...", ["Day01"]))
        self.assertIsNone(QAService(generator=FakeGenerator(TimeoutError())).extract_mindmap_intent("...", ["Day01"]))
        self.assertIsNone(QAService(generator=FakeGenerator("must not be used")).extract_mindmap_intent("   ", ["Day01"]))

    def test_mindmap_retains_metadata_and_rejects_malformed_source_ids(self):
        output = json.dumps({"branches": [{"label": "Nhóm", "children": [
            {"label": "Hỏng", "evidence_id": ["E1"]},
            {"label": "Thật", "evidence_id": "E1", "filename": "fake.pdf", "page_number": 999},
        ]}]})
        evidence = source(filename="Day07/lecture.pdf", day_id="Day07", day_number=7, day_label="Day 07", evidence_type="visual", vision_used=True)
        result = QAService(generator=FakeGenerator(output)).mindmap("RAG", [evidence])
        nodes = result["branches"][0]["nodes"]
        self.assertEqual(len(nodes), 1)
        for key in ("filename", "page_number", "quote", "day_id", "day_number", "day_label", "evidence_type", "vision_used"):
            self.assertEqual(nodes[0][key], evidence[key])

    def test_mindmap_respects_threshold_and_explicit_model_abstention(self):
        generator = FakeGenerator(json.dumps({"branches": []}))
        self.assertEqual(QAService(generator=generator).mindmap("Unknown", [source()])["branches"], [])
        with patch.dict(os.environ, {"NO_ANSWER_THRESHOLD": "0.8"}):
            unused = FakeGenerator("must not run")
            result = QAService(generator=unused).mindmap("Unknown", [source(block_score=0.1)])
            self.assertEqual(result["branches"], [])
            self.assertIsNone(unused.prompt)

    def test_custom_instructions_keep_request_deadline(self):
        from app.runtime import request_deadline
        captured = {}
        client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kw: captured.update(kw) or SimpleNamespace(output_text="{}", status="completed")))
        with request_deadline(0.5):
            AnswerGenerator(client=client, temperature=0).generate("input", instructions="mindmap rules")
        self.assertGreater(captured["timeout"], 0)
        self.assertLessEqual(captured["timeout"], 0.5)
        self.assertEqual(captured["instructions"], "mindmap rules")
        self.assertEqual(captured["temperature"], 0)

    def test_overview_covers_days_model_omits_and_balances_input(self):
        # A model picks only Day01: Day02 must still have a real source branch.
        generator = FakeGenerator(json.dumps({"branches": [{"label": "Selected", "indices": [0]}]}))
        nodes = []
        for day, count in (("Day01", 600), ("Day02", 20)):
            nodes.append((day, [mindmap_node(slide_id=f"{day}_{index}", day_id=day, label=f"Topic {index}") for index in range(count)]))
        overview = QAService(generator=generator).overview_mindmap(nodes)
        self.assertEqual([branch["label"] for branch in overview["branches"]], ["Day 01", "Day 02"])
        self.assertTrue(all(1 <= len(branch["nodes"]) <= 6 for branch in overview["branches"]))
        self.assertTrue(all(node["day_id"] == day for (day, _), branch in zip(nodes, overview["branches"]) for node in branch["nodes"]))
        self.assertIn("Day02: Topic", generator.prompt)
        self.assertLess(len(generator.prompt), 20000)


if __name__ == "__main__":
    unittest.main()
