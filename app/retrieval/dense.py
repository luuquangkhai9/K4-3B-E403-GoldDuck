"""Lazy CPU E5 inference and content-addressed on-disk embedding cache."""

import hashlib
import json
import logging
from pathlib import Path
import os
import tempfile

# Hugging Face's concurrent cache probe can attempt symlinks before Windows
# privilege detection finishes. Ordinary file copies need no administrator.
if os.name == "nt":
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")

import numpy as np

logger = logging.getLogger(__name__)
MODEL_NAME = "intfloat/multilingual-e5-small"


def _atomic_write(path: Path, writer) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    try:
        with os.fdopen(handle, "wb") as stream:
            writer(stream)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class DenseIndex:
    def __init__(self, slides: list[dict], index_dir: Path):
        self.slides = slides
        self.index_dir = index_dir
        self.model = None
        self.embeddings = None
        self.failed = False
        payload = [[slide["slide_id"], slide.get("text", "")] for slide in slides]
        self.fingerprint = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

    def _initialize(self) -> None:
        from sentence_transformers import SentenceTransformer

        try:
            self.model = SentenceTransformer(MODEL_NAME, device="cpu", local_files_only=True)
        except OSError:
            self.model = SentenceTransformer(MODEL_NAME, device="cpu")
        cache_path = self.index_dir / "embeddings.npy"
        meta_path = self.index_dir / "retrieval_meta.json"
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            if (
                metadata.get("fingerprint") == self.fingerprint
                and metadata.get("model") == MODEL_NAME
                and metadata.get("prefix") == "passage: "
            ):
                embeddings = np.load(cache_path, allow_pickle=False)
                if (
                    embeddings.shape == (len(self.slides), 384)
                    and np.isfinite(embeddings).all()
                    and np.allclose(np.linalg.norm(embeddings, axis=1), 1, atol=1e-3)
                ):
                    self.embeddings = embeddings
                    return
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        self.embeddings = np.asarray(
            self.model.encode(
                ["passage: " + slide.get("text", "") for slide in self.slides],
                batch_size=32,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            ),
            dtype=np.float32,
        )
        metadata = {
            "model": MODEL_NAME,
            "fingerprint": self.fingerprint,
            "prefix": "passage: ",
            "slide_ids": [slide["slide_id"] for slide in self.slides],
            "dimensions": int(self.embeddings.shape[1]),
        }
        try:
            _atomic_write(cache_path, lambda stream: np.save(stream, self.embeddings))
            _atomic_write(
                meta_path,
                lambda stream: stream.write(json.dumps(metadata).encode("utf-8")),
            )
        except OSError as error:
            logger.warning("Embedding cache could not be saved: %s", error)

    def search(self, question: str, limit: int = 20) -> list[tuple[int, float]]:
        if self.failed or not self.slides or limit <= 0:
            return []
        try:
            if self.embeddings is None:
                self._initialize()
            query = self.model.encode(
                ["query: " + question],
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )[0]
            scores = self.embeddings @ query
            return [
                (int(index), float(scores[index]))
                for index in np.argsort(-scores, kind="stable")[:limit]
            ]
        except Exception as error:
            self.failed = True
            logger.warning("Dense retrieval unavailable; using BM25: %s", error)
            return []
