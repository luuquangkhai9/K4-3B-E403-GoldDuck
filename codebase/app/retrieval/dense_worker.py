"""Keep CPU model work outside the HTTP process and stop it on timeout."""

import atexit
import hashlib
import json
import logging
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

from app.runtime import bounded_lock, configured_timeout, remaining_timeout
from .config import integer, retrieval_text

PREFIX = "@dense-result:"
logger = logging.getLogger(__name__)


class DenseWorker:
    def __init__(self, slides, index_dir, *, command=None):
        self.index_dir = Path(index_dir)
        payload = [[s["slide_id"], retrieval_text(s)] for s in slides]
        self.fingerprint = hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode("utf-8")).hexdigest()
        self.failed = False
        self.last_error = None
        self.embeddings = None  # readiness marker; the vectors stay in the child
        self.process = None
        self.command = command
        self.replies = queue.Queue()
        self._lock = threading.RLock()
        atexit.register(self.close)

    def close(self):
        atexit.unregister(self.close)
        process, self.process = self.process, None
        if process is None:
            return
        if process.poll() is None:
            process.kill()
        process.wait(timeout=3)
        if process.stdin:
            process.stdin.close()
        if process.stdout:
            process.stdout.close()

    def _start(self):
        environment = dict(os.environ)
        threads = str(min(32, integer("DENSE_CPU_THREADS", 1)))
        for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
            environment[key] = threads
        environment["HF_DEACTIVATE_ASYNC_LOAD"] = "1"
        environment["TOKENIZERS_PARALLELISM"] = "false"
        command = self.command or [sys.executable, "-u", "-m", "app.retrieval.dense_worker", str(self.index_dir)]
        self.process = subprocess.Popen(
            command, cwd=Path(__file__).resolve().parents[2], env=environment,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        process, replies = self.process, self.replies

        def read_replies():
            try:
                for line in process.stdout:
                    if line.startswith(PREFIX):
                        try:
                            replies.put(json.loads(line[len(PREFIX):]))
                        except ValueError:
                            replies.put({"error_type": "InvalidWorkerResponse"})
            except (OSError, ValueError):
                pass
            finally:
                replies.put({"error_type": "WorkerExited"})
        threading.Thread(target=read_replies, daemon=True).start()

    def _call(self, operation, timeout, **parameters):
        with bounded_lock(self._lock):
            if self.failed:
                raise RuntimeError("Dense worker unavailable")
            end = time.monotonic() + remaining_timeout(timeout)
            if self.process is None:
                self._start()
            process = self.process
            message = json.dumps({"operation": operation, "fingerprint": self.fingerprint, **parameters}) + "\n"
            # Pipe writes can block too, particularly if model startup stalls.
            def send():
                try:
                    process.stdin.write(message)
                    process.stdin.flush()
                except (OSError, ValueError):
                    self.replies.put({"error_type": "WorkerPipeClosed"})
            threading.Thread(target=send, daemon=True).start()
            try:
                reply = self.replies.get(timeout=max(0, end - time.monotonic()))
            except queue.Empty as error:
                raise TimeoutError("Dense worker exceeded its time limit") from error
            if reply.get("error_type"):
                self.last_error = reply["error_type"]
                raise RuntimeError(reply["error_type"])
            self.embeddings = True
            return reply["result"]

    def _disable(self, error):
        self.failed = True
        self.last_error = self.last_error or type(error).__name__
        self.close()
        logger.warning("Dense worker stopped (%s); using BM25", self.last_error)

    def search(self, question, limit=20, *, allowed_indices=None):
        if self.failed or limit <= 0 or allowed_indices == []:
            return []
        try:
            return [tuple(item) for item in self._call("search", configured_timeout("DENSE_TIMEOUT_SECONDS", 15),
                question=question, limit=limit, allowed_indices=allowed_indices)]
        except Exception as error:
            self._disable(error)
            return []

    def score_blocks(self, question, texts):
        try:
            return self._call("blocks", configured_timeout("DENSE_BLOCK_TIMEOUT_SECONDS", 5), question=question, texts=texts)
        except Exception as error:
            self._disable(error)
            raise RuntimeError("Dense block scoring unavailable") from error


def main():
    # Imports of Torch/transformers are confined to this process.
    from .dense import DenseIndex
    from .service import RetrievalService
    service = RetrievalService(sys.argv[1], dense_enabled=False)
    service._load()
    dense = DenseIndex(service.slides, service.index_dir)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if request["fingerprint"] != dense.fingerprint:
                raise RuntimeError("IndexChanged")
            if request["operation"] == "search":
                result = dense.search(request["question"], request["limit"], allowed_indices=request["allowed_indices"])
                if dense.failed:
                    raise RuntimeError("DenseUnavailable")
            else:
                result = dense.score_blocks(request["question"], request["texts"])
            reply = {"result": result}
        except Exception as error:
            reply = {"error_type": type(error).__name__}
        print(PREFIX + json.dumps(reply), flush=True)


if __name__ == "__main__":
    main()
