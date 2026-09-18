"""Run with python -m unittest app.retrieval.test_retrieval."""

import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np

from .dense import DenseIndex
from .bm25 import BM25Index
from .fusion import reciprocal_rank_fusion
from .service import RetrievalService


def slide(index, text):
    return {
        "slide_id": f"doc_p{index:04}", "document_id": "doc",
        "filename": "Bài giảng.pdf", "page_index": index - 1,
        "page_number": index, "text": text,
        "blocks": [{"block_id": f"b{index}", "text": text,
                    "bbox": [0.1, 0.2, 0.8, 0.4]}],
    }


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {
            "RERANK_ENABLED": "false", "NEIGHBOR_EXPANSION_ENABLED": "false",
            "RERANK_CANDIDATES": "20", "RERANK_TOP_K": "5",
            "RERANK_TIMEOUT_SECONDS": "10",
            "EVIDENCE_TOP_K": "5", "MAX_EVIDENCE_PER_SLIDE": "2",
        })
        environment.start()
        self.addCleanup(environment.stop)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)
        self.records = [
            slide(1, "Gradient descent tối ưu hàm mất mát bằng đạo hàm."),
            slide(2, "Overfitting xảy ra khi mô hình học quá khớp dữ liệu huấn luyện."),
            slide(3, "Mạng nơ-ron tích chập dùng bộ lọc để xử lý ảnh."),
            slide(4, "Hồi quy tuyến tính dự đoán giá trị liên tục."),
            slide(5, "Cây quyết định phân loại bằng các điều kiện chia nhánh."),
        ]
        self.write(self.records)

    def write(self, records):
        (self.path / "slides.json").write_text(
            json.dumps(records, ensure_ascii=False), encoding="utf-8"
        )

    def test_vietnamese_retrieval_and_exact_citations(self):
        service = RetrievalService(self.path, dense_enabled=False)
        for question, expected in [
            ("Gradient descent là gì?", 1),
            ("Overfitting là gì?", 2),
            ("Mạng nơ-ron tích chập xử lý ảnh thế nào?", 3),
            ("Hồi quy tuyến tính dự đoán gì?", 4),
            ("Cây quyết định chia nhánh ra sao?", 5),
        ]:
            with self.subTest(question=question):
                result = service.retrieve(question)
                self.assertEqual(result["slides"][0]["page_number"], expected)
                evidence = result["evidence"][0]
                self.assertEqual(evidence["quote"], self.records[expected - 1]["text"])
                self.assertEqual(evidence["bbox"], [0.1, 0.2, 0.8, 0.4])
                self.assertIn(f"page={expected}", evidence["viewer_url"])

    def test_empty_missing_unrelated_and_reload(self):
        service = RetrievalService(self.path, dense_enabled=False)
        self.assertEqual(service.retrieve("   "), {"slides": [], "evidence": []})
        self.assertEqual(service.retrieve("xyzzy"), {"slides": [], "evidence": []})
        service.retrieve("descent")
        self.write([slide(9, "Thuật toán mới hoàn toàn")])
        self.assertEqual(service.retrieve("Thuật toán")["slides"][0]["page_number"], 9)
        (self.path / "slides.json").unlink()
        self.assertEqual(service.retrieve("descent"), {"slides": [], "evidence": []})

    def test_dense_failure_preserves_bm25(self):
        fake = types.ModuleType("sentence_transformers")
        fake.SentenceTransformer = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("offline"))
        with patch.dict("sys.modules", {"sentence_transformers": fake}):
            result = RetrievalService(self.path, dense_enabled=True).retrieve("Gradient descent")
        self.assertEqual(result["slides"][0]["page_number"], 1)

    def test_dependency_free_lexical_fallback(self):
        with patch.dict("sys.modules", {"rank_bm25": None}):
            result = RetrievalService(self.path, dense_enabled=False).retrieve("tích chập")
        self.assertEqual(result["slides"][0]["page_number"], 3)

    def test_rrf(self):
        fused = reciprocal_rank_fusion([[(0, 100), (1, 1)], [(1, 0.9)]])
        self.assertEqual(fused[0][0], 1)
        self.assertAlmostEqual(fused[0][1], 1 / 62 + 1 / 61)

    def test_common_terms_rank_strong_matches_first(self):
        texts = ["alpha alpha alpha", "alpha", "alpha filler filler"]
        ranking = BM25Index(texts).search("alpha")
        with patch.dict("sys.modules", {"rank_bm25": None}):
            fallback = BM25Index(texts).search("alpha")
        self.assertEqual([i for i, _ in ranking], [0, 1, 2])
        self.assertEqual([i for i, _ in ranking], [i for i, _ in fallback])

    def test_invalid_index_preserves_last_valid_corpus(self):
        service = RetrievalService(self.path, dense_enabled=False)
        service.retrieve("descent")
        invalid = [
            {"slide_id": 123}, {"slide_id": []}, {"filename": None},
            {"page_number": True}, {"blocks": "invalid"},
            {"blocks": [None]}, {"blocks": [{"text": 123}]},
            {"blocks": [{"text": "descent", "block_id": []}]},
            {"retrieval_text": []}, {"visual_analysis": "invalid"},
        ]
        for update in invalid:
            with self.subTest(update=update):
                self.write([dict(slide(9, "descent changed"), **update)])
                result = service.retrieve("descent")
                self.assertEqual(result["slides"][0]["page_number"], 1)
        self.write([slide(9, "descent recovered")])
        self.assertEqual(service.retrieve("descent")["slides"][0]["page_number"], 9)

    def test_dense_prefixes_cpu_cache_and_invalidation(self):
        calls = []
        fake = types.ModuleType("sentence_transformers")

        class FakeModel:
            def __init__(self, name, device, local_files_only=False):
                self_name = name
                calls.append((self_name, device))

            def encode(self, texts, **kwargs):
                calls.append(texts)
                result = np.zeros((len(texts), 384), dtype=np.float32)
                result[:, 0] = 1
                return result

        fake.SentenceTransformer = FakeModel
        with patch.dict("sys.modules", {"sentence_transformers": fake}):
            first = DenseIndex(self.records, self.path)
            self.assertEqual(len(first.search("tích chập")), 5)
            self.assertIn(("intfloat/multilingual-e5-small", "cpu"), calls)
            self.assertTrue(any(isinstance(c, list) and c[0].startswith("passage: ") for c in calls))
            self.assertIn(["query: tích chập"], calls)
            calls.clear()
            DenseIndex(self.records, self.path).search("tích chập")
            self.assertFalse(any(isinstance(c, list) and c[0].startswith("passage: ") for c in calls))
            calls.clear()
            changed = [slide(1, "Nội dung được cập nhật")]
            DenseIndex(changed, self.path).search("cập nhật")
            self.assertIn(["passage: Nội dung được cập nhật"], calls)


if __name__ == "__main__":
    unittest.main()
