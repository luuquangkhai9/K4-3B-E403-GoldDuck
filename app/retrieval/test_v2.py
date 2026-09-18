"""Offline regression checks for additive retrieval stages."""
import io
import json
import os
import unittest
from unittest.mock import Mock, patch

from . import test_retrieval as fixtures
from .rerank import rerank
from .dense import DenseIndex

slide = fixtures.slide


class RetrievalV2Tests(unittest.TestCase):
    write = fixtures.RetrievalTests.write

    def setUp(self):
        fixtures.RetrievalTests.setUp(self)
        environment = patch.dict(os.environ, {"RERANK_ENABLED": "false",
            "NEIGHBOR_EXPANSION_ENABLED": "true", "NEIGHBOR_DISTANCE": "1",
            "EVIDENCE_TOP_K": "5", "MAX_EVIDENCE_PER_SLIDE": "2"})
        environment.start()
        self.addCleanup(environment.stop)

    def test_rerank_success_and_all_failure_modes(self):
        records = self.records[:2]
        config = {"RERANK_ENABLED": "true", "RERANK_PROVIDER": "cohere",
                  "RERANK_API_KEY": "test", "RERANK_MODEL": "configured-model"}
        with patch.dict(os.environ, config):
            body = {"results": [{"index": 1, "relevance_score": .9},
                                {"index": 0, "relevance_score": .2}]}
            with patch("app.retrieval.rerank.urlopen", return_value=io.StringIO(json.dumps(body))) as call:
                ordered, debug = rerank("question", records, 2)
                self.assertEqual(ordered[0]["slide_id"], records[1]["slide_id"])
                self.assertTrue(debug["reranker_used"])
                payload = json.loads(call.call_args.args[0].data)
                self.assertEqual(payload["model"], "configured-model")
            for response in [{"results": []}, {"results": [{"index": 99, "relevance_score": .9}]},
                             {"results": [{"index": 0, "relevance_score": .9}] * 2}]:
                with patch("app.retrieval.rerank.urlopen", return_value=io.StringIO(json.dumps(response))):
                    ordered, debug = rerank("question", records, 2)
                    self.assertEqual(ordered, records)
                    self.assertTrue(debug["reranker_fallback"])
            with patch("app.retrieval.rerank.urlopen", side_effect=TimeoutError):
                self.assertEqual(rerank("question", records, 2)[0], records)
            with patch.dict(os.environ, {"RERANK_API_KEY": ""}):
                self.assertTrue(rerank("question", records, 2)[1]["reranker_fallback"])

    def test_neighbor_deduplication_and_document_boundary(self):
        from .service import RetrievalService
        foreign = dict(slide(3, "foreign"), slide_id="other_p3", document_id="other", filename="other.pdf")
        self.write(self.records + [foreign])
        service = RetrievalService(self.path, dense_enabled=False)
        result = service.retrieve("Overfitting", top_k=1)
        self.assertEqual([s["page_number"] for s in result["context_slides"]], [1, 3])
        self.assertTrue(all(s["source_role"] == "neighbor" for s in result["context_slides"]))
        service._load()
        neighbors = service._neighbors([self.records[1], self.records[2]])
        self.assertEqual([s["page_number"] for s in neighbors], [1, 4])

    def test_visual_retrieval_and_cache_identity(self):
        from .service import RetrievalService
        visual = slide(1, "")
        visual["retrieval_text"] = "Convolution pooling architecture"
        self.write([visual])
        service = RetrievalService(self.path, dense_enabled=False)
        self.assertEqual(service.retrieve("pooling")["slides"][0]["slide_id"], visual["slide_id"])
        before = DenseIndex([visual], self.path).fingerprint
        visual["retrieval_text"] += " updated"
        self.assertNotEqual(before, DenseIndex([visual], self.path).fingerprint)

    def test_block_ranking_diversity_and_primary_ties(self):
        from .service import RetrievalService
        service = RetrievalService(self.path, dense_enabled=False)
        primary = dict(self.records[1], source_role="primary", blocks=[
            {"block_id": str(i), "text": "Useful block " + str(i)} for i in range(4)]
            + [{"text": "2"}, {"text": "Copyright 2026"}])
        neighbor = dict(self.records[2], source_role="neighbor")
        class Model:
            def score_blocks(self, question, texts):
                self.texts = texts
                return [.9] * len(texts)
        service.dense = Model()
        debug = {}
        evidence = service._evidence("question", [primary, neighbor], rank_blocks=True, debug=debug)
        self.assertEqual(len(evidence), 3)
        self.assertEqual([e["source_role"] for e in evidence], ["primary", "primary", "neighbor"])
        self.assertTrue(all(e["block_score"] == .9 for e in evidence))
        self.assertEqual(debug["block_ranking_method"], "e5")
        self.assertNotIn("2", service.dense.texts)

    def test_dense_block_prefixes_and_cosine_scores(self):
        import numpy as np
        dense = DenseIndex(self.records, self.path)
        dense.embeddings = np.zeros((5, 384))
        calls = []
        class Model:
            def encode(self, texts, **kwargs):
                calls.append(texts)
                self_kwargs = kwargs
                self.assert_normalized = self_kwargs["normalize_embeddings"]
                return np.array([[1., 0.] if "relevant" in text or text.startswith("query:")
                                 else [0., 1.] for text in texts])
        dense.model = Model()
        self.assertEqual(dense.score_blocks("question", ["relevant", "other"]), [1., 0.])
        self.assertEqual(calls, [["passage: relevant", "passage: other"], ["query: question"]])
        self.assertTrue(dense.model.assert_normalized)

    def test_disabled_v2_and_service_rerank_fallback(self):
        from .service import RetrievalService
        service = RetrievalService(self.path, dense_enabled=False)
        with patch.dict(os.environ, {"NEIGHBOR_EXPANSION_ENABLED": "false"}):
            baseline = service.retrieve("descent")
            self.assertEqual(baseline["context_slides"], [])
            with patch.dict(os.environ, {"RERANK_ENABLED": "true", "RERANK_API_KEY": ""}):
                fallback = service.retrieve("descent")
            self.assertEqual(baseline["slides"], fallback["slides"])
            self.assertEqual(baseline["evidence"], fallback["evidence"])
            self.assertTrue(fallback["debug"]["reranker_fallback"])

    def test_rerank_failure_keeps_requested_number_of_hits(self):
        from .service import RetrievalService
        self.write([slide(i, "shared query topic " + str(i)) for i in range(1, 6)])
        with patch.dict(os.environ, {"RERANK_ENABLED": "true", "RERANK_TOP_K": "1", "RERANK_API_KEY": ""}):
            result = RetrievalService(self.path, dense_enabled=False).retrieve("shared query", top_k=3)
        self.assertEqual(len(result["slides"]), 3)
        self.assertTrue(result["debug"]["reranker_fallback"])

    def test_blank_pages_do_not_become_dense_answers(self):
        from .service import RetrievalService
        self.write([slide(1, "")])
        service = RetrievalService(self.path, dense_enabled=True)
        service._load()
        self.assertEqual(service.slides, [])
        self.assertIsNone(service.dense)

    def test_invalid_block_scores_fall_back_without_losing_evidence(self):
        from .service import RetrievalService
        service = RetrievalService(self.path, dense_enabled=False)
        service._load()
        model = Mock()
        model.search.return_value = []
        service.dense = model
        for scores in ([], [float("nan")], [float("inf")]):
            with self.subTest(scores=scores):
                model.score_blocks.return_value = scores
                result = service.retrieve("descent", top_k=1)
                self.assertTrue(result["evidence"])
                self.assertTrue(result["debug"]["block_ranking_fallback"])

    def test_nonfinite_dense_scores_preserve_lexical_fallback(self):
        import numpy as np
        dense = DenseIndex(self.records, self.path)
        dense.embeddings = np.ones((5, 2))
        dense.model = Mock()
        dense.model.encode.return_value = np.array([[float("nan"), 1.]])
        self.assertEqual(dense.search("question"), [])
        self.assertTrue(dense.failed)


if __name__ == "__main__":
    unittest.main()
