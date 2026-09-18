"""Regressions from a real slide whose capability list spans two blocks."""

import copy
import unittest

from .blocks import merge_continuations


class BlockContinuationTests(unittest.TestCase):
    def test_split_capability_sentence_keeps_quote_bbox_and_inputs(self):
        blocks = [
            {"block_id": "b1", "text": "■MCP server công bố tools, resources, và",
             "bbox": [0.05, 0.62, 0.52, 0.66]},
            {"block_id": "b2", "text": "prompts.", "bbox": [0.075, 0.67, 0.18, 0.71]},
        ]
        before = copy.deepcopy(blocks)
        native = "■MCP server công bố tools, resources, và\n   prompts."
        merged = merge_continuations(blocks, native)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["text"], blocks[0]["text"] + "\n" + blocks[1]["text"])
        self.assertEqual(merged[0]["bbox"], [0.05, 0.62, 0.52, 0.71])
        self.assertEqual(merged[0]["block_id"], "b1")
        self.assertEqual(blocks, before)

    def test_different_columns_bullets_footers_and_unverified_order_stay_separate(self):
        first = {"text": "An incomplete sentence and", "bbox": [0.05, 0.60, 0.50, 0.64]}
        second = {"text": "a continuation.", "bbox": [0.07, 0.65, 0.40, 0.69]}
        cases = [
            (first, dict(second, bbox=[0.60, 0.65, 0.90, 0.69]), None),
            (first, dict(second, text="■A new bullet"), None),
            (dict(first, bbox=[0.05, 0.90, 0.50, 0.94]), dict(second, bbox=[0.07, 0.95, 0.40, 0.99]), None),
            (first, second, "An incomplete sentence and interleaved content a continuation."),
            (dict(first, text="A complete sentence."), second, None),
        ]
        for a, b, native in cases:
            with self.subTest(a=a, b=b):
                blocks = [a, b]
                self.assertEqual(merge_continuations(blocks, native or a["text"] + "\n" + b["text"]), blocks)

    def test_continuation_remains_complete_in_ranked_evidence(self):
        from pathlib import Path
        from .service import RetrievalService
        from .bm25 import BM25Index

        service = RetrievalService(Path("data/verification/index"), dense_enabled=False)
        blocks = [{"block_id": "b1", "text": "MCP publishes tools, resources, and", "bbox": [.05, .62, .52, .66]},
                  {"block_id": "b2", "text": "prompts.", "bbox": [.075, .67, .18, .71]}]
        hit = {"slide_id": "s1", "filename": "lecture.pdf", "page_number": 1,
               "text": "MCP publishes tools, resources, and\nprompts.", "blocks": blocks}
        service.slides = [hit]
        service.lexical = BM25Index([hit["text"]])
        evidence = service._evidence("MCP tools resources", [hit], rank_blocks=True)
        self.assertEqual(len(evidence), 1)
        self.assertIn("prompts.", evidence[0]["quote"])
        self.assertIn("bbox=", evidence[0]["viewer_url"])
