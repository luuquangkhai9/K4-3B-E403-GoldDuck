"""Run with python -m unittest app.retrieval.test_retrieval."""

import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np

from .dense import DenseIndex
from .fusion import reciprocal_rank_fusion
from .service import RetrievalService, _group_into_branches


class FakeDense:
    """Minimal stand-in for DenseIndex.search, keyed by branch label instead of embeddings."""

    def __init__(self, slides, scores_by_label):
        self.slides = slides
        self.scores_by_label = scores_by_label

    def search(self, label, limit):
        scores = self.scores_by_label.get(label, {})
        return [(index, scores.get(slide["slide_id"], 0.0)) for index, slide in enumerate(self.slides)]


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

    def test_mindmap_deduplicates_headings_across_day_files(self):
        def day_slide(filename, page, heading, body=""):
            text = heading if not body else f"{heading}\n{body}"
            return {
                "slide_id": f"{filename}_p{page:04}", "document_id": filename,
                "filename": filename, "page_index": page - 1,
                "page_number": page, "text": text,
                "blocks": [{"block_id": f"{filename}_b{page}", "text": text, "bbox": [0, 0, 1, 1]}],
            }

        records = [
            day_slide("Day01/gv1.pdf", 1, "Agenda | Day 01"),
            day_slide("Day01/gv1.pdf", 2, "Overfitting", "chi tiết"),
            day_slide("Day01/gv2.pdf", 1, "agenda   day 01!"),  # same topic, different presenter file
            day_slide("Day01/gv2.pdf", 2, "Regularization"),
            day_slide("Day02/gv1.pdf", 1, "Convolution"),
        ]
        self.write(records)
        service = RetrievalService(self.path, dense_enabled=False)
        result = service.mindmap("Day01")
        self.assertEqual(result["day"], "Day01")
        # The "Agenda" slides (from both presenter files) have no bullet items
        # of their own, so there's no usable agenda — but as meta/outline
        # slides they're still excluded from the outline itself, not just
        # deduplicated, leaving one chunked branch of real content only.
        self.assertEqual(len(result["branches"]), 1)
        nodes = result["branches"][0]["nodes"]
        self.assertEqual([node["label"] for node in nodes], ["Overfitting", "Regularization"])
        self.assertTrue(all(node["filename"].startswith("Day01/") for node in nodes))
        self.assertEqual(nodes[0]["bbox"], [0, 0, 1, 1])
        self.assertIn("page=2", nodes[1]["viewer_url"])
        self.assertIn("file=Day01%2Fgv2.pdf", nodes[1]["viewer_url"])

    def test_mindmap_groups_by_agenda_when_present(self):
        def day_slide(filename, page, heading, extra_lines=()):
            blocks = [{"block_id": f"{filename}_{page}_0", "text": heading, "bbox": [0, 0, 1, 1]}]
            blocks += [
                {"block_id": f"{filename}_{page}_{i}", "text": line, "bbox": [0, 0, 1, 1]}
                for i, line in enumerate(extra_lines, start=1)
            ]
            text = "\n".join([heading, *extra_lines])
            return {
                "slide_id": f"{filename}_p{page:04}", "document_id": filename,
                "filename": filename, "page_index": page - 1,
                "page_number": page, "text": text, "blocks": blocks,
            }

        records = [
            day_slide("Day05/gv.pdf", 1, "Agenda", ["• Retrieval", "• Generation"]),
            day_slide("Day05/gv.pdf", 2, "Retrieval cơ bản"),
            day_slide("Day05/gv.pdf", 3, "Kỹ thuật Retrieval nâng cao"),
            day_slide("Day05/gv.pdf", 4, "Generation với LLM"),
        ]
        self.write(records)
        service = RetrievalService(self.path, dense_enabled=False)
        result = service.mindmap("Day05")
        labels = [branch["label"] for branch in result["branches"]]
        self.assertEqual(labels, ["Retrieval", "Generation"])
        self.assertEqual(
            [node["label"] for node in result["branches"][0]["nodes"]],
            ["Retrieval cơ bản", "Kỹ thuật Retrieval nâng cao"],
        )
        self.assertEqual([node["label"] for node in result["branches"][1]["nodes"]], ["Generation với LLM"])

    def test_mindmap_excludes_recap_slides_from_nodes(self):
        def day_slide(filename, page, heading, extra_lines=()):
            blocks = [{"block_id": f"{filename}_{page}_0", "text": heading, "bbox": [0, 0, 1, 1]}]
            blocks += [
                {"block_id": f"{filename}_{page}_{i}", "text": line, "bbox": [0, 0, 1, 1]}
                for i, line in enumerate(extra_lines, start=1)
            ]
            text = "\n".join([heading, *extra_lines])
            return {
                "slide_id": f"{filename}_p{page:04}", "document_id": filename,
                "filename": filename, "page_index": page - 1,
                "page_number": page, "text": text, "blocks": blocks,
            }

        records = [
            day_slide("Day09/gv.pdf", 1, "Agenda", ["• Retrieval", "• Generation"]),
            day_slide("Day09/gv.pdf", 2, "Retrieval cơ bản"),
            day_slide("Day09/gv.pdf", 3, "Generation với LLM"),
            # A recap slide appearing after the agenda was already found —
            # it should never surface as a clickable topic, since clicking it
            # would just show a bullet list restating the above, not content.
            day_slide("Day09/gv.pdf", 4, "Tổng Kết — Key Takeaways", ["Retrieval", "Generation"]),
        ]
        self.write(records)
        service = RetrievalService(self.path, dense_enabled=False)
        result = service.mindmap("Day09")
        all_labels = [node["label"] for branch in result["branches"] for node in branch["nodes"]]
        self.assertNotIn("Tổng Kết — Key Takeaways", all_labels)
        self.assertEqual(all_labels, ["Retrieval cơ bản", "Generation với LLM"])

    def test_group_into_branches_uses_dense_similarity_when_available(self):
        slides = [{"slide_id": "s1"}, {"slide_id": "s2"}, {"slide_id": "s3"}]
        nodes = [
            {"label": "Cách triển khai mô hình lên production", "slide_id": "s1"},
            {"label": "Rollout với Kubernetes", "slide_id": "s2"},
            {"label": "Chủ đề chẳng liên quan gì", "slide_id": "missing"},  # not in dense.slides
        ]
        dense = FakeDense(slides, {
            "Retrieval": {"s1": 0.9, "s2": 0.85},
            "Generation": {"s1": 0.2, "s2": 0.3},
        })
        branches = _group_into_branches(nodes, ["Retrieval", "Generation"], dense=dense)
        labels = [branch["label"] for branch in branches]
        # Neither node literally shares a word with "Retrieval", so the old
        # token-overlap grouping would have dumped both into "Khác"; dense
        # similarity correctly recognizes both as about retrieval/deployment.
        self.assertEqual(labels, ["Retrieval", "Khác"])
        self.assertEqual([n["label"] for n in branches[0]["nodes"]], [
            "Cách triển khai mô hình lên production", "Rollout với Kubernetes",
        ])
        # A node whose slide isn't in the dense index at all can't be scored,
        # so it falls back to the catch-all rather than being dropped.
        self.assertEqual(branches[1]["nodes"][0]["label"], "Chủ đề chẳng liên quan gì")

    def test_mindmap_rejects_decorative_and_garbled_headings(self):
        def day_slide(filename, page, heading):
            return {
                "slide_id": f"{filename}_p{page:04}", "document_id": filename,
                "filename": filename, "page_index": page - 1,
                "page_number": page, "text": heading,
                "blocks": [{"block_id": f"{filename}_b{page}", "text": heading, "bbox": [0, 0, 1, 1]}],
            }

        records = [
            day_slide("Day06/gv.pdf", 1, "T"),  # decorative single-letter logo
            day_slide("Day06/gv.pdf", 2, ""),  # font-encoding mojibake
            day_slide("Day06/gv.pdf", 3, "12"),  # bare page number
            day_slide("Day06/gv.pdf", 4, "Fine-tuning mô hình"),
        ]
        self.write(records)
        service = RetrievalService(self.path, dense_enabled=False)
        result = service.mindmap("Day06")
        all_labels = [node["label"] for branch in result["branches"] for node in branch["nodes"]]
        self.assertEqual(all_labels, ["Fine-tuning mô hình"])

    def test_rrf(self):
        fused = reciprocal_rank_fusion([[(0, 100), (1, 1)], [(1, 0.9)]])
        self.assertEqual(fused[0][0], 1)
        self.assertAlmostEqual(fused[0][1], 1 / 62 + 1 / 61)

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
