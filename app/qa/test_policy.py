"""Clarification/abstention against real documents, without paid providers."""
import unittest

from app.agent import test_agent as fixtures
from app.qa.policy import QueryPolicy


class PolicyTests(unittest.TestCase):
    def setUp(self):
        fixtures.AgentIntegrationTests.setUp(self)

    def test_short_named_topics_are_not_ambiguous(self):
        policy = QueryPolicy(self.retrieval)
        for question in ("CNN", "Transformer", "RAG", "CNN là gì?"):
            self.assertIsNone(policy.clarification(question))

    def test_ambiguity_returns_real_scoped_sources_without_model(self):
        response = self.client.post("/api/chat", json={"question": "cái này chạy thế nào", "scope": ["Day01"]})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual(self.generator.calls, [])
        self.assertEqual(result["clarification"]["original_query"], "cái này chạy thế nào")
        self.assertTrue(result["clarification"]["options"])
        self.check_sources(result["clarification"]["options"], "Day01")

    def check_sources(self, options, day):
        for option in options:
            for source in option["sources"]:
                self.assertEqual(source["day_id"], day)
                record = next(record for record in self.records if record["slide_id"] == source["slide_id"])
                self.assertIn(source["quote"], record["text"])
                self.assertEqual(self.client.get(source["viewer_url"]).status_code, 200)

    def test_unknown_identifier_abstains_offline_with_scoped_suggestions(self):
        for endpoint in ("/api/ask", "/api/chat"):
            response = self.client.post(endpoint, json={"question": "UnknownTopic987654 là gì?", "scope": ["Day02"]})
            self.assertEqual(response.status_code, 200, response.text)
            result = response.json()
            self.assertIn(result["status"], ("abstained", "no_evidence"))
            self.assertEqual(result["citations"], [])
            self.check_sources(result["suggestions"], "Day02")
        self.assertEqual(self.generator.calls, [])

    def test_no_literal_translation_does_not_prove_absence(self):
        self.assertIsNone(self.retrieval.topic_supported("cơ chế chú ý"))

    def test_missing_compound_entity_does_not_match_single_letter(self):
        self.assertFalse(self.retrieval.topic_supported("Q-learning"))

    def test_invalid_scope_validated_before_clarification(self):
        for question, scope, code in (("cái này", ["Day99"], 404),
                                      ("cái này day 2", ["Day01"], 422)):
            response = self.client.post("/api/chat", json={"question": question, "scope": scope})
            self.assertEqual(response.status_code, code, response.text)
        self.assertEqual(self.generator.calls, [])

    def test_selected_topic_preserves_document_mindmap_intent(self):
        question = "tạo mindmap các tài liệu về cái này"
        response = self.client.post("/api/chat", json={"question": question,
                                    "clarification_topic": "Transformer", "scope": ["Day01"]})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual((result["task"], result["status"]), ("study_materials", "completed"))
        self.assertEqual(result["debug"]["agent"]["original_question"], question)
        self.assertEqual({document["day_id"] for document in result["documents"]}, {"Day01"})

    def test_day_overview_and_context_followup_are_not_ambiguous(self):
        policy = QueryPolicy(self.retrieval)
        self.assertIsNone(policy.clarification("tạo mindmap", scope=["Day01"]))
        self.assertIsNone(policy.clarification("tạo mindmap các tài liệu đó", context={"topic": "Transformer"}))

    def test_empty_custom_topic_rejected(self):
        response = self.client.post("/api/chat", json={"question": "cái này", "clarification_topic": "  "})
        self.assertEqual(response.status_code, 422)
