"""Frozen retrieval interface shared with the QA and API agents.

INDEX_DIR defaults to data/index relative to the project root. Missing indexes
return empty results; a running service reloads the corpus after ingestion.
"""

import json
import logging
import math
import os
from pathlib import Path
import threading
from urllib.parse import urlencode

from .bm25 import BM25Index, tokenize
from .fusion import reciprocal_rank_fusion

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class RetrievalService:
    def __init__(self, index_dir=None, dense_enabled=None):
        configured = Path(index_dir or os.getenv("INDEX_DIR", "data/index"))
        self.index_dir = configured if configured.is_absolute() else PROJECT_ROOT / configured
        self.dense_enabled = (
            os.getenv("DENSE_ENABLED", "true").strip().lower() not in {"false", "0", "no", "off"}
            if dense_enabled is None else bool(dense_enabled)
        )
        self.slides = []
        self.lexical = BM25Index([])
        self.dense = None
        self._signature = None
        self._lock = threading.RLock()

    def _load(self):
        path = self.index_dir / "slides.json"
        try:
            stat = path.stat()
            signature = (stat.st_mtime_ns, stat.st_size)
        except FileNotFoundError:
            self.slides = []
            self.lexical = BM25Index([])
            self.dense = None
            self._signature = None
            return
        if signature == self._signature:
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            records = payload.get("slides", []) if isinstance(payload, dict) else payload
            if not isinstance(records, list):
                raise ValueError("slides.json must contain a slide list")
            slides = []
            seen = set()
            for slide in records:
                if not isinstance(slide, dict):
                    raise ValueError("slide must be an object")
                if not all(key in slide for key in ("slide_id", "filename", "page_number")):
                    raise ValueError("slide missing citation metadata")
                if slide["slide_id"] in seen:
                    raise ValueError("duplicate slide_id")
                if not isinstance(slide.get("text", ""), str):
                    raise ValueError("slide text must be a string")
                if not isinstance(slide["page_number"], int) or slide["page_number"] < 1:
                    raise ValueError("page_number must be one-based")
                seen.add(slide["slide_id"])
                if slide.get("text", "").strip():
                    slides.append(slide)
            lexical = BM25Index([slide["text"] for slide in slides])
        except (OSError, ValueError, TypeError) as error:
            # Ingestion may be in the middle of a write. Keep the last valid
            # corpus and retry on the next request rather than cache the failure.
            logger.warning("Slide index not ready: %s", error)
            return
        self.slides = slides
        self.lexical = lexical
        self.dense = None
        if self.dense_enabled and slides:
            try:
                from .dense import DenseIndex

                self.dense = DenseIndex(slides, self.index_dir)
            except ImportError as error:
                logger.warning("Dense dependencies unavailable; using BM25: %s", error)
        self._signature = signature

    def retrieve(self, question: str, top_k: int = 5) -> dict:
        if not isinstance(question, str):
            raise TypeError("question must be a string")
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 0:
            raise ValueError("top_k must be a non-negative integer")
        if not question.strip() or top_k == 0:
            return {"slides": [], "evidence": []}
        with self._lock:
            self._load()
            limit = max(20, top_k)
            lexical = self.lexical.search(question, limit)
            dense = self.dense.search(question, limit) if self.dense else []
            rankings = [ranking for ranking in (lexical, dense) if ranking]
            fused = reciprocal_rank_fusion(rankings, top_k)
            hits = [
                dict(self.slides[index], score=score, rank=rank)
                for rank, (index, score) in enumerate(fused, start=1)
            ]
            return {"slides": hits, "evidence": self._evidence(question, hits[:3])}

    def _evidence(self, question, hits):
        query = set(tokenize(question))
        candidates = []
        for slide_rank, hit in enumerate(hits):
            blocks = hit.get("blocks") or []
            if not blocks:
                blocks = [{"block_id": None, "text": hit["text"], "bbox": None}]
            for block_rank, block in enumerate(blocks):
                text = block.get("text", "")
                if not isinstance(text, str) or not text.strip():
                    continue
                tokens = set(tokenize(text))
                matching = query & tokens
                weighted_overlap = sum(
                    math.log(1 + len(self.slides) / (1 + self.lexical.document_frequency[token]))
                    for token in matching
                )
                score = weighted_overlap / math.sqrt(max(1, len(tokens)))
                candidates.append((score, slide_rank, block_rank, hit, block))
        candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        evidence = []
        for _, _, _, hit, block in candidates[:5]:
            evidence_id = f"E{len(evidence) + 1}"
            parameters = {"file": hit["filename"], "page": hit["page_number"], "evidence": evidence_id}
            bbox = block.get("bbox")
            # Ingestion's contract is normalized coordinates. For compatibility,
            # normalize PDF coordinates only when dimensions are provided.
            if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                try:
                    bbox = [float(value) for value in bbox]
                    if not all(math.isfinite(value) for value in bbox):
                        bbox = None
                    elif max(bbox) > 1:
                        width = hit.get("page_width", hit.get("width"))
                        height = hit.get("page_height", hit.get("height"))
                        bbox = [bbox[0] / width, bbox[1] / height, bbox[2] / width, bbox[3] / height] if width and height else None
                    if bbox is not None and not (
                        0 <= bbox[0] <= bbox[2] <= 1 and 0 <= bbox[1] <= bbox[3] <= 1
                    ):
                        bbox = None
                except (ValueError, TypeError, ZeroDivisionError):
                    bbox = None
            else:
                bbox = None
            if bbox is not None:
                parameters["bbox"] = ",".join(str(value) for value in bbox)
            evidence.append({
                "evidence_id": evidence_id,
                "slide_id": hit["slide_id"],
                "block_id": block.get("block_id"),
                "filename": hit["filename"],
                "page_number": hit["page_number"],
                "quote": block["text"],
                "bbox": bbox,
                "viewer_url": "/viewer?" + urlencode(parameters),
            })
        return evidence


_default_service = None
_default_lock = threading.Lock()


def retrieve(question: str, top_k: int = 5) -> dict:
    global _default_service
    with _default_lock:
        if _default_service is None:
            _default_service = RetrievalService()
    return _default_service.retrieve(question, top_k)
