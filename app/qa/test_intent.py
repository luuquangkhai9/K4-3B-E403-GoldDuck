"""Explicit mindmap scopes must survive unavailable/incorrect model parsing."""

import unittest

from .intent import parse_explicit_mindmap_scope


class MindmapScopeIntentTests(unittest.TestCase):
    def test_range_in_screenshot_has_no_topic(self):
        self.assertEqual(parse_explicit_mindmap_scope("tao mindmap từ day 1 đến day 3"),
                         {"day": None, "scope": ["Day01", "Day02", "Day03"], "topic": None})

    def test_ranges_and_lists_keep_topic_and_every_day(self):
        cases = [
            ("tạo mindmap về Transformer từ day 1 đến day 3", ["Day01", "Day02", "Day03"], "Transformer"),
            ("vẽ sơ đồ tư duy buổi 1 tới buổi 3", ["Day01", "Day02", "Day03"], None),
            ("tạo mindmap day 1-3", ["Day01", "Day02", "Day03"], None),
            ("tạo mindmap day 1 và day 3", ["Day01", "Day03"], None),
            ("tạo mindmap day 1, 2 và 3", ["Day01", "Day02", "Day03"], None),
            ("tạo mindmap về RAG day 1 và day 3", ["Day01", "Day03"], "RAG"),
            ("tạo mindmap từ day 1 đến day 1", ["Day01"], None),
        ]
        for question, scope, topic in cases:
            with self.subTest(question=question):
                result = parse_explicit_mindmap_scope(question)
                self.assertEqual(result["scope"], scope)
                self.assertEqual(result["topic"], topic)

    def test_invalid_ranges_do_not_become_global_search(self):
        for question in ("mindmap day 3 đến day 1", "mindmap day 0-3", "mindmap day 1-9999", "mindmap day 0 và day 1"):
            with self.subTest(question=question), self.assertRaises(ValueError):
                parse_explicit_mindmap_scope(question)
        self.assertEqual(parse_explicit_mindmap_scope("mindmap day 98-99")["scope"], ["Day98", "Day99"])

    def test_single_day_and_non_mindmap_keep_existing_model_path(self):
        self.assertIsNone(parse_explicit_mindmap_scope("tạo mindmap buổi học số 7 về RAG"))
        self.assertIsNone(parse_explicit_mindmap_scope("so sánh kiến thức day 1 và day 3"))
