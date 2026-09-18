"""Regressions for stalled model processes, queued requests and topic lookup."""

import json
import os
import platform
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.main import app
from app.qa.generator import AnswerGenerator
from app.qa.service import QAService
from app.retrieval.dense_worker import DenseWorker
from app.retrieval.query import prepare_query
from app.retrieval.service import RetrievalService
from app.runtime import bounded_lock, configure_windows_runtime, remaining_timeout, request_deadline

QUESTION = "Tôi muốn học về tranformers, tôi cần học những tài liệu nào nằm ở ngày nào"
SLEEP = [sys.executable, "-u", "-c", "import time; time.sleep(60)"]


class TimeoutTests(unittest.TestCase):
    def worker(self, command):
        worker = DenseWorker([], Path.cwd(), command=command)
        self.addCleanup(worker.close)
        return worker

    def test_stalled_startup_is_killed_and_not_retried(self):
        worker = self.worker(SLEEP)
        with patch.dict(os.environ, {"DENSE_TIMEOUT_SECONDS": "0.15"}):
            start = time.monotonic()
            self.assertEqual(worker.search("transformer"), [])
        self.assertLess(time.monotonic() - start, 1.5)
        self.assertTrue(worker.failed)
        self.assertEqual(worker.last_error, "TimeoutError")
        self.assertIsNone(worker.process)
        with patch.object(worker, "_start", side_effect=AssertionError("must not restart")):
            self.assertEqual(worker.search("transformer"), [])

    def test_deadline_also_bounds_a_full_stdin_pipe(self):
        worker = self.worker(SLEEP)
        with request_deadline(0.15):
            start = time.monotonic()
            with self.assertRaises(RuntimeError):
                worker.score_blocks("transformer", ["x" * 1000000])
        self.assertLess(time.monotonic() - start, 1.5)
        self.assertIsNone(worker.process)

    def test_worker_is_reused_and_ignores_non_protocol_output(self):
        script = """import sys,json
for line in sys.stdin:
    request=json.loads(line)
    print('model startup chatter', flush=True)
    result=[[0,0.8]] if request['operation']=='search' else [0.7]*len(request['texts'])
    print('@dense-result:'+json.dumps({'result':result}),flush=True)
"""
        worker = self.worker([sys.executable, "-u", "-c", script])
        self.assertEqual(worker.search("transformer"), [(0, 0.8)])
        process = worker.process
        self.assertEqual(worker.score_blocks("transformer", ["one", "two"]), [0.7, 0.7])
        self.assertIs(worker.process, process)
        worker.close()
        self.assertIsNotNone(process.poll())

    def test_child_exit_uses_fallback_immediately(self):
        worker = self.worker([sys.executable, "-c", "pass"])
        self.assertEqual(worker.search("transformer"), [])
        self.assertTrue(worker.failed)
        self.assertIsNone(worker.process)

    def test_nested_deadline_cannot_extend_original_budget(self):
        with request_deadline(0.1):
            with request_deadline(10):
                self.assertLessEqual(remaining_timeout(20), 0.1)
        self.assertEqual(remaining_timeout(20), 20)

    def test_queued_lock_has_a_time_limit(self):
        lock = threading.Lock()
        lock.acquire()
        self.addCleanup(lock.release)
        with request_deadline(0.05):
            start = time.monotonic()
            with self.assertRaises(TimeoutError):
                with bounded_lock(lock):
                    self.fail("held lock acquired")
        self.assertLess(time.monotonic() - start, 0.5)

    def test_api_reports_busy_instead_of_waiting_forever(self):
        service = RetrievalService(dense_enabled=False)
        qa = QAService(generator=AnswerGenerator(api_key=""))
        with service._lock, patch("app.api.main.get_services", return_value=(service, qa)), patch.dict(os.environ, {"REQUEST_TIMEOUT_SECONDS": "0.05"}), TestClient(app) as client:
            start = time.monotonic()
            response = client.post("/api/ask", json={"question": "Transformer là gì?"})
            self.assertEqual(response.status_code, 503, response.text)
            self.assertLess(time.monotonic() - start, 0.5)
            self.assertEqual(client.get("/api/health").status_code, 200)

    def test_wmi_stall_uses_python_fallback_and_is_not_retried(self):
        release = threading.Event()
        calls = []
        def probe(*args):
            calls.append(args)
            release.wait(2)
            return ("Windows",)
        try:
            with patch("app.runtime.os.name", "nt"), patch.object(platform, "_wmi_query", probe, create=True):
                configure_windows_runtime()
                start = time.monotonic()
                with self.assertRaises(OSError):
                    platform._wmi_query("OS", "Version")
                self.assertLess(time.monotonic() - start, 0.7)
                with self.assertRaises(OSError):
                    platform._wmi_query("OS", "Version")
                self.assertEqual(len(calls), 1)
        finally:
            release.set()

    def test_healthy_wmi_is_preserved_and_wrapper_is_idempotent(self):
        def probe(*args):
            return args
        with patch("app.runtime.os.name", "nt"), patch.object(platform, "_wmi_query", probe, create=True):
            configure_windows_runtime()
            wrapper = platform._wmi_query
            self.assertEqual(wrapper("OS", "Version"), ("OS", "Version"))
            configure_windows_runtime()
            self.assertIs(platform._wmi_query, wrapper)

    def test_topic_typo_repair_preserves_unrecognized_names(self):
        query, discovery, fixes = prepare_query(QUESTION, {"transformers": 3, "transformer": 2})
        self.assertTrue(discovery)
        self.assertEqual(query, "transformers transformer")
        self.assertEqual(fixes, {"tranformers": "transformers"})
        self.assertEqual(prepare_query("Tôi muốn học về qwertyzxc, tài liệu nào?", {"transformer": 3})[0], "qwertyzxc")
        self.assertEqual(prepare_query("Tranformers là gì?", {"transformers": 3})[0], "Tranformers là gì?")

    def test_real_api_answers_when_dense_startup_stalls(self):
        with tempfile.TemporaryDirectory() as temporary:
            records = [
                {"slide_id": f"slide{i}", "filename": filename, "page_number": 1,
                 "text": text, "blocks": [{"text": text}]}
                for i, (filename, text) in enumerate([
                    ("Day04/attention.pdf", "Transformers use self-attention."),
                    ("Day05/transformer.pdf", "Transformer models encode tokens."),
                    ("Day09/advanced.pdf", "Transformers use attention layers."),
                    ("Day01/intro.pdf", "Tài liệu bài học ngày đầu tiên về convolution."),
                ])
            ]
            Path(temporary, "slides.json").write_text(json.dumps(records), encoding="utf-8")
            service = RetrievalService(temporary, dense_enabled=True)
            previous = {name: getattr(app.state, name, None) for name in ("retrieval_service", "qa_service")}
            def restore():
                if service.dense:
                    service.dense.close()
                for name, value in previous.items():
                    if value is None:
                        if hasattr(app.state, name):
                            delattr(app.state, name)
                    else:
                        setattr(app.state, name, value)
            self.addCleanup(restore)
            app.state.retrieval_service = service
            app.state.qa_service = QAService(generator=AnswerGenerator(api_key=""))
            environment = {"DENSE_TIMEOUT_SECONDS": "0.15", "REQUEST_TIMEOUT_SECONDS": "2",
                "RERANK_ENABLED": "false", "NEIGHBOR_EXPANSION_ENABLED": "false", "NO_ANSWER_THRESHOLD": "",
                "NO_ANSWER_ENABLED": "true", "EVIDENCE_TOP_K": "5", "TOP_K": "5"}
            def stalled_worker(slides, index_dir):
                return DenseWorker(slides, index_dir, command=SLEEP)
            with patch.dict(os.environ, environment), patch("app.retrieval.dense_worker.DenseWorker", side_effect=stalled_worker), TestClient(app) as client:
                start = time.monotonic()
                response = client.post("/api/ask", json={"question": QUESTION})
                self.assertLess(time.monotonic() - start, 1.5)
                self.assertEqual(response.status_code, 200, response.text)
                payload = response.json()
                self.assertTrue(payload["debug"]["dense_fallback"])
                self.assertEqual({c["day_id"] for c in payload["citations"]}, {"Day04", "Day05", "Day09"})
                self.assertIn("Day04/attention.pdf", payload["answer"])
                self.assertNotIn("Day01/intro.pdf", payload["answer"])
                self.assertEqual(client.get("/api/days").status_code, 200)
                scoped = client.post("/api/ask", json={"question": QUESTION, "day_id": "Day05"})
                self.assertEqual(scoped.status_code, 200, scoped.text)
                self.assertEqual({c["day_id"] for c in scoped.json()["citations"]}, {"Day05"})


if __name__ == "__main__":
    unittest.main()
