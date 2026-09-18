"""Frozen retrieval interface shared with the QA and API agents.

INDEX_DIR defaults to data/index relative to the project root. Missing indexes
return empty results; a running service reloads the corpus after ingestion.
"""

import json
import logging
import math
import os
import re
from pathlib import Path
import threading
from urllib.parse import urlencode

from .bm25 import BM25Index, tokenize
from .fusion import reciprocal_rank_fusion

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

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
                bbox = block.get("bbox")
                return cleaned, (list(bbox) if isinstance(bbox, (list, tuple)) and len(bbox) == 4 else None)
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


def _group_into_branches(nodes: list[dict], agenda_items: list[str] | None, dense=None) -> list[dict]:
    if agenda_items:
        buckets: list[list[dict]] = [[] for _ in agenda_items]
        other = []
        if dense is not None and dense.slides:
            # Semantic assignment: rank every slide in the corpus against each
            # branch topic through the dense embedding index, then put each
            # node under whichever topic scores its own slide highest. This
            # catches slides that don't literally share words with the topic
            # name — plain token overlap left most headings unmatched,
            # dumping the bulk of a lesson into one giant "Khác" bucket.
            branch_scores = [dict(dense.search(item, limit=len(dense.slides))) for item in agenda_items]
            slide_index_by_id = {slide["slide_id"]: index for index, slide in enumerate(dense.slides)}
            for node in nodes:
                slide_index = slide_index_by_id.get(node.get("slide_id"))
                best_index, best_score = -1, 0.0
                if slide_index is not None:
                    for branch_index, scores in enumerate(branch_scores):
                        score = scores.get(slide_index, 0.0)
                        if score > best_score:
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

    def retrieve(self, question: str, top_k: int = 5, scope: list[str] | None = None) -> dict:
        if not isinstance(question, str):
            raise TypeError("question must be a string")
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 0:
            raise ValueError("top_k must be a non-negative integer")
        if not question.strip() or top_k == 0:
            return {"slides": [], "evidence": []}
        with self._lock:
            self._load()
            # A learner reviewing specific days wants answers grounded only in
            # those days, not pulled in from the rest of the corpus. The
            # lexical/dense backends search the whole corpus regardless, so
            # widen their search window to cover everything when scoped and
            # filter hits down to the requested day folders afterward.
            scoped = bool(scope)
            prefixes = tuple(s if s.endswith("/") else s + "/" for s in scope) if scoped else None
            limit = len(self.slides) if scoped else max(20, top_k)
            lexical = self.lexical.search(question, limit)
            dense = self.dense.search(question, limit) if self.dense else []
            if scoped:
                def in_scope(index: int) -> bool:
                    return self.slides[index]["filename"].startswith(prefixes)
                lexical = [item for item in lexical if in_scope(item[0])][: max(20, top_k)]
                dense = [item for item in dense if in_scope(item[0])][: max(20, top_k)]
            rankings = [ranking for ranking in (lexical, dense) if ranking]
            fused = reciprocal_rank_fusion(rankings, top_k)
            hits = [
                dict(self.slides[index], score=score, rank=rank)
                for rank, (index, score) in enumerate(fused, start=1)
            ]
            return {"slides": hits, "evidence": self._evidence(question, hits[:5])}

    @property
    def available_scopes(self) -> list[str]:
        """Day folders (e.g. "Day03") a caller can pass as retrieve(scope=...)."""
        with self._lock:
            self._load()
            return sorted({slide["filename"].split("/", 1)[0] for slide in self.slides if "/" in slide["filename"]})

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
        prefix = day if day.endswith("/") else day + "/"
        pages = sorted(
            (slide for slide in self.slides if slide["filename"].startswith(prefix)),
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
                "viewer_url": "/viewer?" + urlencode(parameters),
            })
        return nodes, agenda_items

    def mindmap_nodes(self, day: str) -> list[dict]:
        """The flat topic-node list for one day, ungrouped (for an LLM to organize into branches)."""
        if not isinstance(day, str) or not day.strip():
            raise ValueError("day must be a non-empty string")
        with self._lock:
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
        with self._lock:
            self._load()
            nodes, agenda_items = self._mindmap_nodes(day)
            return {"day": day, "branches": _group_into_branches(nodes, agenda_items, dense=self.dense)}

    def _evidence(self, question, hits, limit=12, top_slide_cap=7):
        query = set(tokenize(question))
        by_slide = [[] for _ in hits]
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
                by_slide[slide_rank].append((score, slide_rank, block_rank, hit, block))
        # The top-ranked page can hold the answer in blocks that share few
        # literal words with the question (e.g. numbered list items under a
        # header that matches the query instead), so guarantee its blocks
        # reach the model in reading order. But near-duplicate PDFs of the
        # same lecture often crowd the top ranks with repeated content, so
        # also guarantee every other top page at least one shot at its
        # best-scoring block before any page gets a second slot.
        selected = list(by_slide[0][:top_slide_cap]) if by_slide else []
        seen_positions = {(item[1], item[2]) for item in selected}
        for slide_rank in range(1, len(hits)):
            best = max(by_slide[slide_rank], default=None, key=lambda item: item[0])
            if best is not None and best[0] > 0 and len(selected) < limit:
                selected.append(best)
                seen_positions.add((best[1], best[2]))
        remaining = [
            item
            for scored in by_slide
            for item in scored
            if (item[1], item[2]) not in seen_positions
        ]
        remaining.sort(key=lambda item: (-item[0], item[1], item[2]))
        selected += remaining[: max(0, limit - len(selected))]
        evidence = []
        for _, _, _, hit, block in selected[:limit]:
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
