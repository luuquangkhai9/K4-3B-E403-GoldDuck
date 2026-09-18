"""Mindmap integration with the isolated dense interface and metadata filters."""

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from app.runtime import request_deadline
from .dense_worker import DenseWorker
from .service import RetrievalService, _group_into_branches


def record(index, day, text):
    return {
        "slide_id": f"s{index}", "document_id": f"doc{day}",
        "filename": f"nested/Day{day:02d}/lesson.pdf", "page_number": index + 1,
        "day_id": f"Day{day:02d}", "day_number": day, "day_label": f"Day {day:02d}",
        "text": text, "blocks": [{"block_id": f"b{index}", "text": text, "bbox": [0, 0, 1, 1]}],
    }


class MindmapWorkerTests(unittest.TestCase):
    def test_grouping_maps_global_indices_without_dense_slides(self):
        slides = [record(0, 2, "outside"), record(1, 1, "Retrieval"),
                  record(2, 2, "outside"), record(3, 1, "Generation")]
        nodes = [{"slide_id": "s1", "label": "First"}, {"slide_id": "s3", "label": "Second"}]
        calls = []

        class WorkerInterface:
            failed = False
            def search(self, question, limit, *, allowed_indices):
                calls.append((question, limit, allowed_indices))
                return [(1, 0.9), (3, 0.1)] if question == "Retrieval" else [(1, 0.1), (3, 0.9)]

        branches = _group_into_branches(nodes, ["Retrieval", "Generation"], WorkerInterface(), slides=slides)
        self.assertEqual([b["label"] for b in branches], ["Retrieval", "Generation"])
        self.assertEqual([b["nodes"][0]["slide_id"] for b in branches], ["s1", "s3"])
        self.assertEqual([c[2] for c in calls], [[1, 3], [1, 3]])

    def test_empty_or_failed_dense_really_falls_back_to_lexical(self):
        slides = [record(0, 1, "Retrieval"), record(1, 1, "Generation")]
        nodes = [{"slide_id": s["slide_id"], "label": s["text"]} for s in slides]
        for failure in (False, True):
            class WorkerInterface:
                failed = failure
                def search(self, *args, **kwargs):
                    if failure:
                        raise AssertionError("Failed workers must not be called")
                    return []
            branches = _group_into_branches(nodes, ["Retrieval", "Generation"], WorkerInterface(), slides=slides)
            self.assertEqual([b["label"] for b in branches], ["Retrieval", "Generation"])

    def test_stalled_real_worker_is_stopped_and_mindmap_is_still_grouped(self):
        slides = [record(0, 1, "Retrieval"), record(1, 1, "Generation")]
        nodes = [{"slide_id": s["slide_id"], "label": s["text"]} for s in slides]
        with tempfile.TemporaryDirectory() as directory:
            worker = DenseWorker(slides, Path(directory), command=[sys.executable, "-u", "-c", "import time; time.sleep(60)"])
            self.addCleanup(worker.close)
            with patch.dict(os.environ, {"DENSE_TIMEOUT_SECONDS": "0.1"}), request_deadline(1):
                branches = _group_into_branches(nodes, ["Retrieval", "Generation"], worker, slides=slides)
            self.assertTrue(worker.failed)
            self.assertIsNone(worker.process)
            self.assertEqual([b["label"] for b in branches], ["Retrieval", "Generation"])

    def test_multi_day_scope_filters_dense_and_neighbors_using_metadata(self):
        records = [record(0, 1, "Shared retrieval"), record(1, 3, "Shared retrieval"), record(2, 2, "Shared retrieval")]
        # Day metadata must work when source filenames have no Day folder.
        records[2]["filename"] = "custom/lesson.pdf"
        calls = []
        class WorkerInterface:
            failed = False
            def search(self, question, limit, *, allowed_indices=None):
                calls.append(allowed_indices)
                return [(index, 0.9) for index in allowed_indices]
            def score_blocks(self, question, texts):
                return [0.9] * len(texts)
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            "RERANK_ENABLED": "false", "NEIGHBOR_EXPANSION_ENABLED": "true",
        }):
            Path(directory, "slides.json").write_text(json.dumps(records), encoding="utf-8")
            service = RetrievalService(directory, dense_enabled=False)
            service._load()
            service.dense = WorkerInterface()
            result = service.retrieve("Shared retrieval", top_k=20, scope=["D01", "day2"])
        self.assertEqual(calls, [[0, 2]])
        self.assertEqual({s["day_id"] for s in result["primary_slides"]}, {"Day01", "Day02"})
        self.assertTrue(all(s["day_id"] in {"Day01", "Day02"}
                            for s in result["primary_slides"] + result["context_slides"] + result["evidence"]))


if __name__ == "__main__":
    unittest.main()
