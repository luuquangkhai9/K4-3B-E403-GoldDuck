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
from .query import normalize_topic, prepare_query
from app.ingestion.metadata import build_day_catalog, enrich_slide_metadata, normalize_day_id, record_day_metadata, resolve_day_scope
from app.runtime import bounded_lock
from app.viewer.evidence import normalized_bbox

logger = logging.getLogger(__name__)
from app.paths import runtime_root

PROJECT_ROOT = runtime_root(Path(__file__).resolve().parents[2])


_AGENDA_MARKERS = ("agenda", "nội dung", "noi dung", "mục lục", "muc luc", "outline")
# Recap/summary slides ("Tổng kết", "Key Takeaways") restate ground already
# covered elsewhere rather than holding their own content, so — like the
# agenda slide itself — they should never become a clickable topic node;
# clicking one would just land on a page of bullet-point recap, not the
# actual material the label promises.
_META_MARKERS = _AGENDA_MARKERS + (
    "tổng kết", "tong ket", "key takeaway", "tóm tắt", "tom tat", "recap", "summary",
)
# Font subsetting on some lecture PDFs maps glyphs into the Unicode private-use
# area (or drops them to U+FFFD) instead of their real character, so extracted
# "headings" can be mojibake. Reject those, plus decorative single letters and
# bare page numbers, rather than surfacing them as mindmap topics.
_GARBLED_CHARS = re.compile(r"[-�\x00-\x08\x0B\x0C\x0E-\x1F]")
_BULLET_PREFIX = re.compile(r"^[\-–—•*\d]+[.)]?\s*")
# Slides titled "Agenda" are sometimes a timetable (Time | Activities | ...)
# rather than a topic list; its column headers pass the heading-quality check
# but aren't real topics, so reject the common ones by name.
_GENERIC_AGENDA_WORDS = {
    "time", "activities", "activity", "agenda", "description", "note", "notes",
    "thời gian", "hoạt động", "nội dung", "mô tả", "ghi chú", "stt",
}
# Slide footers ("Giảng viên (VinUni) / AICB - Ngày 1 / 02/04/2026 / 14 / 67")
# score well when their page is relevant, but every line is page furniture,
# not content — a block only qualifies if it has at least one line that
# isn't pure boilerplate.
_BOILERPLATE_LINE = re.compile(
    r"^\s*(?:gi[aả]ng vi[eê]n\b|aicb\b|\d{1,2}/\d{1,2}/\d{2,4}\s*$|\d+\s*/\s*\d+\s*$)",
    re.IGNORECASE,
)


def _is_usable_evidence_text(text: str) -> bool:
    # Some decks prefix bullets with an icon-font glyph that lands in the
    # private-use area (e.g. " Tính mỏng manh..."); stripping it before
    # judging the block keeps the real sentence that follows instead of
    # rejecting the whole block over one decorative character.
    cleaned = _GARBLED_CHARS.sub("", text)
    if sum(1 for ch in cleaned if ch.isalpha()) < 2:
        return False
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    return bool(lines) and not all(_BOILERPLATE_LINE.match(line) for line in lines)


def _clean_heading(text: str, *, max_length: int = 90) -> str | None:
    heading = text.strip()
    if not heading or _GARBLED_CHARS.search(heading):
        return None
    if sum(1 for ch in heading if ch.isalpha()) < 2:
        return None
    return heading if len(heading) <= max_length else heading[:max_length].rstrip() + "…"


def _heading_for_slide(slide: dict, *, block_limit: int = 3) -> tuple[str, list[float] | None] | None:
    """The first clean text line near the top of the page, used as its topic label.

    Returns the heading together with its block's bbox so a mindmap node can
    highlight exactly where that heading sits on the page — without it, the
    viewer just shows the whole page with nothing marking why it's relevant.
    """
    for block in (slide.get("blocks") or [])[:block_limit]:
        text = block.get("text", "")
        if not isinstance(text, str):
            continue
        for line in text.splitlines():
            cleaned = _clean_heading(line)
            if cleaned:
                return cleaned, normalized_bbox(block.get("bbox"))
    return None


def _agenda_items(slide: dict, heading: str) -> list[str]:
    items = []
    seen = set()
    for block in slide.get("blocks") or []:
        text = block.get("text", "")
        if not isinstance(text, str):
            continue
        for raw_line in text.splitlines():
            line = _BULLET_PREFIX.sub("", raw_line).strip()
            cleaned = _clean_heading(line, max_length=60)
            if not cleaned or cleaned == heading:
                continue
            key = cleaned.lower()
            if key in seen or key in _GENERIC_AGENDA_WORDS:
                continue
            seen.add(key)
            items.append(cleaned)
    return items


_MAX_NODES_PER_BRANCH = 8


def _cap_branch_sizes(branches: list[dict]) -> list[dict]:
    """Split any branch bigger than the cap into numbered parts.

    A popular agenda topic (or the whole lesson, in the no-agenda fallback)
    can collect far more slides than the others, making one branch tower
    over the rest and pushing the tree's vertical center way off-screen.
    Splitting keeps every slide reachable without one branch dominating
    the layout.
    """
    capped = []
    for branch in branches:
        nodes = branch["nodes"]
        if len(nodes) <= _MAX_NODES_PER_BRANCH:
            capped.append(branch)
            continue
        chunks = [nodes[i:i + _MAX_NODES_PER_BRANCH] for i in range(0, len(nodes), _MAX_NODES_PER_BRANCH)]
        for index, chunk in enumerate(chunks, start=1):
            capped.append({"label": f"{branch['label']} ({index}/{len(chunks)})", "nodes": chunk})
    return capped


def _group_into_branches(nodes: list[dict], agenda_items: list[str] | None, dense=None, *, slides=None) -> list[dict]:
    if agenda_items:
        buckets: list[list[dict]] = [[] for _ in agenda_items]
        other = []
        corpus = slides if slides is not None else getattr(dense, "slides", [])
        branch_scores = []
        if dense is not None and getattr(dense, "failed", False) is not True and corpus:
            # Semantic assignment: rank every slide in the corpus against each
            # branch topic through the dense embedding index, then put each
            # node under whichever topic scores its own slide highest. This
            # catches slides that don't literally share words with the topic
            # name — plain token overlap left most headings unmatched,
            # dumping the bulk of a lesson into one giant "Khác" bucket.
            try:
                if slides is None:
                    # Compatibility for callers supplying an in-process index.
                    branch_scores = [dict(dense.search(item, limit=len(corpus))) for item in agenda_items]
                else:
                    node_ids = {node.get("slide_id") for node in nodes}
                    allowed = [index for index, slide in enumerate(corpus) if slide["slide_id"] in node_ids]
                    branch_scores = [dict(dense.search(item, limit=len(allowed), allowed_indices=allowed))
                                     for item in agenda_items]
                if not any(any(math.isfinite(score) and score > 0 for score in scores.values())
                           for scores in branch_scores) or getattr(dense, "failed", False) is True:
                    branch_scores = []
            except Exception as exc:
                logger.warning("Dense mindmap grouping unavailable (%s); using lexical grouping", type(exc).__name__)
                branch_scores = []
        if branch_scores:
            slide_index_by_id = {slide["slide_id"]: index for index, slide in enumerate(corpus)}
            for node in nodes:
                slide_index = slide_index_by_id.get(node.get("slide_id"))
                best_index, best_score = -1, 0.0
                if slide_index is not None:
                    for branch_index, scores in enumerate(branch_scores):
                        score = scores.get(slide_index, 0.0)
                        if math.isfinite(score) and score > best_score:
                            best_index, best_score = branch_index, score
                (buckets[best_index] if best_index >= 0 else other).append(node)
        else:
            topic_tokens = [set(tokenize(item)) for item in agenda_items]
            for node in nodes:
                node_tokens = set(tokenize(node["label"]))
                best_index, best_score = -1, 0
                for index, tokens in enumerate(topic_tokens):
                    score = len(tokens & node_tokens)
                    if score > best_score:
                        best_index, best_score = index, score
                (buckets[best_index] if best_index >= 0 else other).append(node)
        # If nothing scored well enough to land in a real branch, the agenda
        # wasn't useful (e.g. a timetable slide) — fall through to the chunk
        # fallback instead of dumping every node into "Khác".
        if any(buckets):
            branches = [
                {"label": label, "nodes": bucket}
                for label, bucket in zip(agenda_items, buckets) if bucket
            ]
            if other:
                branches.append({"label": "Khác", "nodes": other})
            return _cap_branch_sizes(branches)
    if not nodes:
        return []
    # No agenda slide to anchor real topics on: fall back to evenly sized
    # chunks (at most ~8 branches) so the outline still reads as branches.
    chunk_size = max(4, -(-len(nodes) // 8))
    branches = [
        {"label": f"Phần {index + 1}", "nodes": nodes[start:start + chunk_size]}
        for index, start in enumerate(range(0, len(nodes), chunk_size))
    ]
    return _cap_branch_sizes(branches)


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

    def normalize_topic(self, topic):
        with bounded_lock(self._lock):
            self._load()
            normalized, aliases, corrections = normalize_topic(topic, self.lexical.document_frequency)
            return {"topic": normalized, "aliases": aliases, "corrections": corrections}

    def topic_supported(self, topic, *, scope=None):
        """A conservative offline absence check, not a semantic relevance score."""
        days = resolve_day_scope(scope=scope)
        with bounded_lock(self._lock):
            self._load()
            terms = set(tokenize(topic))
            if not terms:
                return False
            texts = [retrieval_text(slide) for slide in self.slides
                     if days is None or slide["day_id"] in days]
            if re.fullmatch(r"[A-Za-z]+-[A-Za-z]+", topic.strip()):
                phrase = re.escape(topic.strip()).replace(r"\-", r"[\s-]+")
                return any(re.search(rf"(?<!\w){phrase}(?!\w)", text, re.I) for text in texts)
            if terms & {"transformer", "transformers"}:
                terms |= {"transformer", "transformers"}
            if any(terms & set(tokenize(text)) for text in texts):
                return True
            if re.fullmatch(r"[A-Za-z0-9_]{8,}", topic.strip()) and re.search(r"\d", topic):
                return False
            # A translation/synonym can have no lexical overlap. Leave that
            # case to semantic retrieval rather than equating overlap with truth.
            return None

    def subject_terms(self, question, *, scope=None):
        days = resolve_day_scope(scope=scope)
        with bounded_lock(self._lock):
            self._load()
            vocab = (self.lexical.document_frequency if days is None else
                     BM25Index([retrieval_text(slide) for slide in self.slides if slide["day_id"] in days]).document_frequency)
            return [word for word in tokenize(question) if word in vocab]

    def concept_suggestions(self, question, *, scope=None, limit=3):
        """Local lexical/header suggestions with real source links; no API calls."""
        days = resolve_day_scope(scope=scope)
        with bounded_lock(self._lock):
            self._load()
            slides = [slide for slide in self.slides if days is None or slide["day_id"] in days]
            lexical = self.lexical if days is None else BM25Index([retrieval_text(slide) for slide in slides])
            ranked = [slides[index] for index, _ in lexical.search(question, 30)]
            # If the query has no lexical match, these are available topics,
            # not alleged answers or allegedly nearest semantic neighbors.
            candidates = ranked or slides
            suggestions = []
            seen = set()
            for slide in candidates:
                heading = _heading_for_slide(slide)
                if not heading:
                    continue
                label, bbox = heading
                key = " ".join(tokenize(label))
                if not key or key in seen or any(marker in label.casefold() for marker in _META_MARKERS):
                    continue
                if label.casefold() in {"vinuni", "welcome", "giảng viên", "aicb"}:
                    continue
                seen.add(key)
                evidence_id = f"S{len(suggestions) + 1}"
                parameters = {"file": slide["filename"], "page": slide["page_number"], "evidence": evidence_id}
                if bbox is not None:
                    parameters["bbox"] = ",".join(map(str, bbox))
                source = {"evidence_id": evidence_id, "slide_id": slide["slide_id"],
                          "document_id": slide["document_id"], "filename": slide["filename"],
                          "page_number": slide["page_number"], **record_day_metadata(slide),
                          "quote": label.removesuffix("…"), "bbox": bbox,
                          "viewer_url": "/viewer?" + urlencode(parameters), "evidence_type": "native"}
                suggestions.append({"id": slide["slide_id"], "label": label,
                                    "query": label, "sources": [source]})
                if len(suggestions) >= min(3, max(1, limit)):
                    break
            return suggestions

    def retrieve(self, question: str, top_k: int = 5, *, day_id=None, scope=None,
                 document_discovery=None, evidence_top_k=None) -> dict:
        if not isinstance(question, str):
            raise TypeError("question must be a string")
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 0:
            raise ValueError("top_k must be a non-negative integer")
        if document_discovery is not None and type(document_discovery) is not bool:
            raise ValueError("document_discovery must be boolean")
        if evidence_top_k is not None and (type(evidence_top_k) is not int or not 1 <= evidence_top_k <= 40):
            raise ValueError("evidence_top_k must be between 1 and 40")
        canonical = normalize_day_id(day_id) if day_id is not None else None
        days = resolve_day_scope(day_id, scope)
        if not question.strip() or top_k == 0:
            return {"slides": [], "evidence": []}
        with bounded_lock(self._lock):
            self._load()
            limit = max(integer("RERANK_CANDIDATES", 20), top_k)
            search_question, discovery, corrections = prepare_query(question, self.lexical.document_frequency)
            if document_discovery is not None:
                discovery = document_discovery
            if discovery:
                limit = max(80 if document_discovery else 40, limit)
            if days is not None:
                allowed = [i for i, slide in enumerate(self.slides) if slide["day_id"] in days]
                if not allowed:
                    debug = {"scope_filter": days}
                    if canonical is not None:
                        debug["day_filter"] = canonical
                    return {"slides": [], "evidence": [], "debug": debug}
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
            if document_discovery is True:
                selected_k = top_k
            primary, debug = rerank(search_question, hits, selected_k)
            debug["dense_used"] = bool(dense)
            debug["dense_fallback"] = bool(self.dense_enabled and not dense)
            if corrections:
                debug["query_corrections"] = corrections
            if discovery:
                debug["document_discovery"] = True
            if canonical is not None:
                debug["day_filter"] = canonical
            if days is not None:
                debug["scope_filter"] = days
            if debug.get("reranker_fallback"):
                primary = hits[:top_k]
            primary = [dict(hit, source_role="primary", rank=rank)
                       for rank, hit in enumerate(primary, 1)]
            debug["first_stage_count"] = len(hits)
            try:
                context = self._neighbors(primary) if enabled("NEIGHBOR_EXPANSION_ENABLED") else []
                if days is not None:
                    context = [slide for slide in context if slide["day_id"] in days]
                debug["neighbor_fallback"] = False
            except Exception:
                context = []
                debug["neighbor_fallback"] = True
            expanded = primary + context
            try:
                evidence = self._evidence(search_question, expanded, rank_blocks=True, debug=debug,
                                          document_discovery=discovery, evidence_top_k=evidence_top_k)
            except Exception as error:
                logger.warning("Block ranking failed; using V1 evidence: %s", type(error).__name__)
                debug["block_ranking_fallback"] = True
                debug["block_ranking_method"] = "lexical_v1"
                evidence = self._evidence(search_question, primary if discovery else primary[:3],
                                          document_discovery=discovery, evidence_top_k=evidence_top_k)
            return {"slides": primary, "primary_slides": primary,
                    "context_slides": context, "evidence": evidence, "debug": debug}

    def search_documents(self, topic, *, scope=None, limit=12):
        """Explicit document discovery, independent of the user's phrasing."""
        return self.retrieve(topic, top_k=max(1, min(12, limit)), scope=scope,
                             document_discovery=True, evidence_top_k=max(1, min(12, limit)))

    def read_document_evidence(self, document_ids, question, *, scope=None, pages_per_document=3):
        """Read bounded real pages from selected documents; no second model call."""
        if len(document_ids) > 12 or not 1 <= pages_per_document <= 3:
            raise ValueError("Too many documents or pages")
        days = resolve_day_scope(scope=scope)
        requested = set(document_ids)
        with bounded_lock(self._lock):
            self._load()
            selected = [slide for slide in self.slides if slide["document_id"] in requested
                        and (days is None or slide["day_id"] in days)]
            index = BM25Index([retrieval_text(slide) for slide in selected])
            rankings = dict(index.search(question, len(selected)))
            evidence = []
            for document_id in document_ids:
                candidates = [(rankings.get(i, 0), slide) for i, slide in enumerate(selected)
                              if slide["document_id"] == document_id]
                candidates.sort(key=lambda pair: (-pair[0], pair[1]["page_number"]))
                for _, slide in candidates[:pages_per_document]:
                    # Native and Vision remain distinct sources, as in the QA pipeline.
                    for kind, text in (("native", slide.get("text", "")),
                                       ("visual", visual_evidence_text(slide))):
                        if not text or not _is_usable_evidence_text(text):
                            continue
                        # Keep a verbatim window around a query term instead of
                        # sending entire decks or cutting off a late topic mention.
                        terms = [re.escape(token) for token in tokenize(question) if len(token) > 2]
                        match = re.search(r"(?<!\w)(?:" + "|".join(terms) + r")(?!\w)", text, re.I) if terms else None
                        start = max(0, match.start() - 300) if match else 0
                        evidence.append({
                            "slide_id": slide["slide_id"], "document_id": document_id,
                            "filename": slide["filename"], "page_number": slide["page_number"],
                            **record_day_metadata(slide), "quote": text[start:start + 1600], "bbox": None,
                            "block_id": slide["slide_id"] + "_visual" if kind == "visual" else None,
                            "evidence_type": kind, "source_role": "primary",
                            "vision_used": bool(visual_evidence_text(slide)),
                        })
            return evidence

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

    @property
    def available_scopes(self) -> list[str]:
        """Day folders (e.g. "Day03") a caller can pass as retrieve(scope=...)."""
        with bounded_lock(self._lock):
            self._load()
            return [day["day_id"] for day in self.catalog["days"]]

    def _mindmap_nodes(self, day: str) -> tuple[list[dict], list[str] | None]:
        """Deduplicated, meta-slide-filtered topic nodes for one day, plus any detected agenda.

        Each page's heading (its first clean text line) doubles as a topic
        label. A day bundles several near-duplicate PDFs from different
        presenters covering the same material, so headings are deduplicated
        (case/punctuation-insensitive) to distinct topics instead of repeating
        the same node once per file. Slides that look like an agenda or a
        recap ("Agenda | Day 03", "Tổng Kết") never become nodes themselves —
        clicking one would just show a bullet list restating other pages, not
        content of its own — but the agenda's bullet items are captured to
        use as topic-branch labels.
        """
        canonical = normalize_day_id(day)
        pages = sorted(
            (slide for slide in self.records if slide["day_id"] == canonical),
            key=lambda slide: (slide["filename"], slide["page_number"]),
        )
        nodes = []
        seen = set()
        agenda_items = None
        for slide in pages:
            found = _heading_for_slide(slide)
            if not found:
                continue
            heading, bbox = found
            key = re.sub(r"[^\w]+", " ", heading.lower()).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            if any(marker in key for marker in _META_MARKERS):
                if agenda_items is None and any(marker in key for marker in _AGENDA_MARKERS):
                    items = _agenda_items(slide, heading)
                    if len(items) >= 2:
                        agenda_items = items
                continue  # agenda/recap slides restate other pages, never a topic node themselves
            parameters = {"file": slide["filename"], "page": slide["page_number"]}
            if bbox is not None:
                parameters["bbox"] = ",".join(str(value) for value in bbox)
            nodes.append({
                "label": heading,
                "filename": slide["filename"],
                "page_number": slide["page_number"],
                "bbox": bbox,
                "slide_id": slide["slide_id"],
                "document_id": slide.get("document_id"),
                **record_day_metadata(slide),
                "vision_used": slide.get("visual_analysis", {}).get("status") == "success"
                               if isinstance(slide.get("visual_analysis"), dict) else False,
                "viewer_url": "/viewer?" + urlencode(parameters),
            })
        return nodes, agenda_items

    def mindmap_nodes(self, day: str) -> list[dict]:
        """The flat topic-node list for one day, ungrouped (for an LLM to organize into branches)."""
        if not isinstance(day, str) or not day.strip():
            raise ValueError("day must be a non-empty string")
        with bounded_lock(self._lock):
            self._load()
            nodes, _ = self._mindmap_nodes(day)
            return nodes

    def mindmap(self, day: str) -> dict:
        """A rule-based topic outline for one day, built without any LLM call.

        Dense embeddings (when available) assign each node to whichever
        agenda topic it's most semantically similar to; otherwise plain word
        overlap is used. See `mindmap_nodes` for the AI-organized alternative.
        """
        if not isinstance(day, str) or not day.strip():
            raise ValueError("day must be a non-empty string")
        with bounded_lock(self._lock):
            self._load()
            nodes, agenda_items = self._mindmap_nodes(day)
            return {"day": normalize_day_id(day),
                    "branches": _group_into_branches(nodes, agenda_items, dense=self.dense, slides=self.slides)}

    def _evidence(self, question, hits, rank_blocks=False, debug=None, document_discovery=False,
                  evidence_top_k=None):
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
                if not _is_usable_evidence_text(text):
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
            if len(evidence) >= (evidence_top_k if evidence_top_k is not None else
                                 integer("EVIDENCE_TOP_K", 5) if rank_blocks else 5):
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
                "vision_used": hit.get("visual_analysis", {}).get("status") == "success"
                               if isinstance(hit.get("visual_analysis"), dict) else False,
                "viewer_url": "/viewer?" + urlencode(parameters),
            })
        return evidence


_default_service = None
_default_lock = threading.Lock()


def retrieve(question: str, top_k: int = 5, *, day_id=None, scope=None) -> dict:
    global _default_service
    with _default_lock:
        if _default_service is None:
            _default_service = RetrievalService()
    return _default_service.retrieve(question, top_k, day_id=day_id, scope=scope)
