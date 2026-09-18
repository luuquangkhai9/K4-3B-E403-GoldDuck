"""Frozen retrieval interface shared with the QA and API agents.

INDEX_DIR defaults to data/index relative to the project root. Missing indexes
return empty results; a running service reloads the corpus after ingestion.
"""

import json
from copy import deepcopy
import logging
import math
import os
import re
from pathlib import Path
import threading
from urllib.parse import urlencode

from .bm25 import BM25Index, tokenize
from .blocks import merge_continuations
from .fusion import reciprocal_rank_fusion
from .config import enabled, integer, retrieval_text, visual_evidence_text
from .rerank import rerank
from .query import prepare_query
from app.ingestion.metadata import build_day_catalog, enrich_slide_metadata, normalize_day_id, record_day_metadata
from app.runtime import bounded_lock

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class RetrievalService:
    def __init__(self, index_dir=None, dense_enabled=None, *, dense_isolated=True):
        configured = Path(index_dir or os.getenv("INDEX_DIR", "data/index"))
        self.index_dir = configured if configured.is_absolute() else PROJECT_ROOT / configured
        self.dense_enabled = (
            os.getenv("DENSE_ENABLED", "true").strip().lower() not in {"false", "0", "no", "off"}
            if dense_enabled is None else bool(dense_enabled)
        )
        self.slides = []
        self.records = []
        self.catalog = build_day_catalog([])
        self.lexical = BM25Index([])
        self.dense = None
        self.dense_isolated = dense_isolated
        self._signature = None
        self._lock = threading.RLock()

    def _load(self):
        path = self.index_dir / "slides.json"
        try:
            stat = path.stat()
            signature = (stat.st_mtime_ns, stat.st_size)
        except FileNotFoundError:
            if self.dense is not None and hasattr(self.dense, "close"):
                self.dense.close()
            self.slides = []
            self.records = []
            self.catalog = build_day_catalog([])
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
            all_records = []
            seen = set()
            for slide in records:
                if not isinstance(slide, dict):
                    raise ValueError("slide must be an object")
                if not all(key in slide for key in ("slide_id", "filename", "page_number")):
                    raise ValueError("slide missing citation metadata")
                for key in ("slide_id", "filename"):
                    if not isinstance(slide[key], str) or not slide[key].strip():
                        raise ValueError(f"{key} must be a non-empty string")
                if slide["slide_id"] in seen:
                    raise ValueError("duplicate slide_id")
                if not isinstance(slide.get("text", ""), str):
                    raise ValueError("slide text must be a string")
                if slide.get("retrieval_text") is not None and not isinstance(slide["retrieval_text"], str):
                    raise ValueError("retrieval_text must be a string or null")
                if slide.get("visual_analysis") is not None and not isinstance(slide["visual_analysis"], dict):
                    raise ValueError("visual_analysis must be an object or null")
                if isinstance(slide["page_number"], bool) or not isinstance(slide["page_number"], int) or slide["page_number"] < 1:
                    raise ValueError("page_number must be one-based")
                blocks = slide.get("blocks")
                if blocks is not None:
                    if not isinstance(blocks, list):
                        raise ValueError("slide blocks must be a list")
                    for block in blocks:
                        if not isinstance(block, dict) or not isinstance(block.get("text", ""), str):
                            raise ValueError("block must be an object with string text")
                        if block.get("block_id") is not None and not isinstance(block["block_id"], str):
                            raise ValueError("block_id must be a string or null")
                seen.add(slide["slide_id"])
                slide = enrich_slide_metadata(slide)
                total = slide.get("document_total_pages")
                if total is not None and (type(total) is not int or total < slide["page_number"]):
                    raise ValueError("document_total_pages must cover every slide")
                all_records.append(slide)
                if retrieval_text(slide).strip():
                    slides.append(slide)
            lexical = BM25Index([retrieval_text(slide) for slide in slides])
            catalog = build_day_catalog(all_records)
        except (OSError, ValueError, TypeError) as error:
            # Ingestion may be in the middle of a write. Keep the last valid
            # corpus and retry on the next request rather than cache the failure.
            logger.warning("Slide index not ready: %s", error)
            return
        self.slides = slides
        self.records = all_records
        self.catalog = catalog
        self.lexical = lexical
        if self.dense is not None and hasattr(self.dense, "close"):
            self.dense.close()
        self.dense = None
        if self.dense_enabled and slides:
            try:
                if self.dense_isolated:
                    from .dense_worker import DenseWorker
                    self.dense = DenseWorker(slides, self.index_dir)
                else:
                    from .dense import DenseIndex
                    self.dense = DenseIndex(slides, self.index_dir)
            except Exception as error:
                logger.warning("Dense dependencies unavailable; using BM25: %s", error)
        self._signature = signature

    def list_days(self):
        with bounded_lock(self._lock):
            self._load()
            return deepcopy(self.catalog)

    def get_day(self, day_id):
        canonical = normalize_day_id(day_id)
        with bounded_lock(self._lock):
            self._load()
            for day in self.catalog["days"]:
                if day["day_id"] == canonical:
                    return deepcopy(day)
        raise KeyError(canonical)

    def get_day_slides(self, day_id, *, offset=0, limit=100):
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError("Invalid pagination")
        with bounded_lock(self._lock):
            day = self.get_day(day_id)
            slides = sorted((s for s in self.records if s["day_id"] == day["day_id"]),
                            key=lambda s: (s["filename"], s["page_number"]))
            return {**{k: day[k] for k in ("day_id", "day_number", "day_label")},
                    "total": len(slides), "offset": offset, "limit": limit,
                    "slides": deepcopy(slides[offset:offset + limit])}

    def retrieve(self, question: str, top_k: int = 5, *, day_id=None) -> dict:
        if not isinstance(question, str):
            raise TypeError("question must be a string")
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 0:
            raise ValueError("top_k must be a non-negative integer")
        canonical = normalize_day_id(day_id) if day_id is not None else None
        if not question.strip() or top_k == 0:
            return {"slides": [], "evidence": []}
        with bounded_lock(self._lock):
            self._load()
            limit = max(integer("RERANK_CANDIDATES", 20), top_k)
            search_question, discovery, corrections = prepare_query(question, self.lexical.document_frequency)
            if discovery:
                limit = max(40, limit)
            if canonical is not None:
                allowed = [i for i, slide in enumerate(self.slides) if slide["day_id"] == canonical]
                if not allowed:
                    return {"slides": [], "evidence": [], "debug": {"day_filter": canonical}}
                scoped = BM25Index([retrieval_text(self.slides[i]) for i in allowed])
                lexical = [(allowed[i], score) for i, score in scoped.search(search_question, limit)]
                dense = self.dense.search(search_question, limit, allowed_indices=allowed) if self.dense else []
            else:
                lexical = self.lexical.search(search_question, limit)
                dense = self.dense.search(search_question, limit) if self.dense else []
            rankings = [ranking for ranking in (lexical, dense) if ranking]
            fused = reciprocal_rank_fusion(rankings, limit)
            hits = [
                dict(self.slides[index], score=score, rank=rank)
                for rank, (index, score) in enumerate(fused, start=1)
            ]
            if not hits:
                return {"slides": [], "evidence": []}
            if discovery:
                documents = set()
                distinct = []
                for hit in hits:
                    if hit["filename"] not in documents:
                        documents.add(hit["filename"])
                        distinct.append(hit)
                hits = distinct
            selected_k = min(top_k, integer("RERANK_TOP_K", top_k)) if enabled("RERANK_ENABLED") else top_k
            primary, debug = rerank(search_question, hits, selected_k)
            debug["dense_used"] = bool(dense)
            debug["dense_fallback"] = bool(self.dense_enabled and not dense)
            if corrections:
                debug["query_corrections"] = corrections
            if discovery:
                debug["document_discovery"] = True
            if canonical is not None:
                debug["day_filter"] = canonical
            if debug.get("reranker_fallback"):
                primary = hits[:top_k]
            primary = [dict(hit, source_role="primary", rank=rank)
                       for rank, hit in enumerate(primary, 1)]
            debug["first_stage_count"] = len(hits)
            try:
                context = self._neighbors(primary) if enabled("NEIGHBOR_EXPANSION_ENABLED") else []
                if canonical is not None:
                    context = [slide for slide in context if slide["day_id"] == canonical]
                debug["neighbor_fallback"] = False
            except Exception:
                context = []
                debug["neighbor_fallback"] = True
            expanded = primary + context
            try:
                evidence = self._evidence(search_question, expanded, rank_blocks=True, debug=debug,
                                          document_discovery=discovery)
            except Exception as error:
                logger.warning("Block ranking failed; using V1 evidence: %s", type(error).__name__)
                debug["block_ranking_fallback"] = True
                debug["block_ranking_method"] = "lexical_v1"
                evidence = self._evidence(search_question, primary if discovery else primary[:3],
                                          document_discovery=discovery)
            return {"slides": primary, "primary_slides": primary,
                    "context_slides": context, "evidence": evidence, "debug": debug}

    def _neighbors(self, primary):
        seen = {hit["slide_id"] for hit in primary}
        pages = {(slide.get("document_id", slide["filename"]), slide["filename"], slide["page_number"]): slide
                 for slide in self.slides}
        context = []
        distance = integer("NEIGHBOR_DISTANCE", 1, minimum=0)
        for hit in primary:
            for offset in range(-distance, distance + 1):
                neighbor = pages.get((hit.get("document_id", hit["filename"]), hit["filename"], hit["page_number"] + offset))
                if neighbor is not None and neighbor["slide_id"] not in seen:
                    seen.add(neighbor["slide_id"])
                    context.append(dict(neighbor, source_role="neighbor", neighbor_of=hit["slide_id"], distance=offset))
        return context

    def _evidence(self, question, hits, rank_blocks=False, debug=None, document_discovery=False):
        query = set(tokenize(question))
        candidates = []
        for slide_rank, hit in enumerate(hits):
            blocks = list(hit.get("blocks") or [])
            if not blocks:
                blocks = [{"block_id": None, "text": hit.get("text", ""), "bbox": None}]
            if rank_blocks:
                blocks = merge_continuations(blocks, hit.get("text", ""))
            visual_text = visual_evidence_text(hit)
            if visual_text:
                blocks.append({"block_id": hit["slide_id"] + "_visual", "text": visual_text,
                               "bbox": None, "evidence_type": "visual"})
            for block_rank, block in enumerate(blocks):
                text = block.get("text", "")
                if not isinstance(text, str) or not text.strip():
                    continue
                if rank_blocks and (re.fullmatch(r"\s*(?:page\s*)?\d+\s*", text, re.I)
                                    or re.match(r"\s*(?:copyright\b|©|all rights reserved\b)", text, re.I)
                                    or len(text.strip()) < 3):
                    continue
                tokens = set(tokenize(text))
                matching = query & tokens
                weighted_overlap = sum(
                    math.log(1 + len(self.slides) / (1 + self.lexical.document_frequency[token]))
                    for token in matching
                )
                score = weighted_overlap / math.sqrt(max(1, len(tokens)))
                candidates.append((score, slide_rank, block_rank, hit, block))
        # Document lookup needs a topic mention plus filename/day metadata.
        # Encoding every block again adds unnecessary latency to this flow.
        if rank_blocks and not document_discovery and self.dense and getattr(self.dense, "failed", False) is not True and candidates:
            scores = self.dense.score_blocks(question, [item[4]["text"] for item in candidates])
            if len(scores) != len(candidates) or not all(math.isfinite(score) for score in scores):
                raise ValueError("Invalid block scores")
            candidates = [(score, *item[1:]) for score, item in zip(scores, candidates)]
            if debug is not None:
                debug["block_ranking_method"] = "e5"
        elif debug is not None:
            debug["block_ranking_method"] = "lexical_document_discovery" if document_discovery else "lexical"
        if debug is not None:
            debug["block_ranking_fallback"] = bool(rank_blocks and not document_discovery and self.dense_enabled and
                                                    (not self.dense or getattr(self.dense, "failed", False) is True))
        candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        evidence = []
        per_slide = {}
        documents = set()
        for block_score, _, _, hit, block in candidates:
            if len(evidence) >= (integer("EVIDENCE_TOP_K", 5) if rank_blocks else 5):
                break
            if rank_blocks and per_slide.get(hit["slide_id"], 0) >= integer("MAX_EVIDENCE_PER_SLIDE", 2):
                continue
            if document_discovery and hit["filename"] in documents:
                continue
            documents.add(hit["filename"])
            per_slide[hit["slide_id"]] = per_slide.get(hit["slide_id"], 0) + 1
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
                        0 <= bbox[0] < bbox[2] <= 1 and 0 <= bbox[1] < bbox[3] <= 1
                    ):
                        bbox = None
                except (ValueError, TypeError, ZeroDivisionError, OverflowError):
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
                "document_id": hit.get("document_id"),
                **record_day_metadata(hit),
                "page_number": hit["page_number"],
                "quote": block["text"],
                "bbox": bbox,
                "block_score": block_score,
                "source_role": hit.get("source_role", "primary"),
                "evidence_type": block.get("evidence_type", "native"),
                "viewer_url": "/viewer?" + urlencode(parameters),
            })
        return evidence


_default_service = None
_default_lock = threading.Lock()


def retrieve(question: str, top_k: int = 5, *, day_id=None) -> dict:
    global _default_service
    with _default_lock:
        if _default_service is None:
            _default_service = RetrievalService()
    return _default_service.retrieve(question, top_k, day_id=day_id)
