"""Frozen QAService interface with deterministic source metadata."""

import json
import logging
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .generator import AnswerGenerator
from .prompts import (
    INSUFFICIENT_EVIDENCE,
    MINDMAP_SYSTEM_PROMPT,
    ORGANIZE_SYSTEM_PROMPT,
    build_mindmap_prompt,
    build_organize_prompt,
    build_prompt,
)

logger = logging.getLogger(__name__)
_CITATION = re.compile(r"\[\s*E[^\[\]\n]*\]", re.IGNORECASE)
_VALID_ID = re.compile(r"\[E[1-9]\d*\]")
_CODE_FENCE = re.compile(r"^```[a-zA-Z]*\n?|```$")
_MAX_MINDMAP_BRANCHES = 8
_MAX_MINDMAP_NODES_PER_BRANCH = 10
_MAX_ORGANIZE_NODES_PER_BRANCH = 6  # a representative overview, not every slide — see ORGANIZE_SYSTEM_PROMPT
# Items are short label strings, so even a generous cap is cheap in tokens;
# a lesson bundling many near-duplicate presenter decks can genuinely have
# a few hundred deduplicated headings (observed: 379), and silently
# truncating leaves real content unreachable from the mindmap entirely.
_MAX_ORGANIZE_NODES = 500


def _bbox(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        coordinates = [float(v) for v in value]
    except (TypeError, ValueError, OverflowError):
        return None
    if not all(math.isfinite(v) and 0 <= v <= 1 for v in coordinates):
        return None
    x0, y0, x1, y1 = coordinates
    return coordinates if x0 <= x1 and y0 <= y1 else None


def prepare_evidence(evidence: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Keep exact quotes, skip unusable sources, and never mutate retrieval output."""
    prepared = []
    seen = set()
    for raw in evidence:
        if not isinstance(raw, Mapping):
            continue
        quote = raw.get("quote", raw.get("text", ""))
        filename = raw.get("filename")
        page = raw.get("page_number")
        if not isinstance(quote, str) or not quote.strip():
            continue
        if not isinstance(filename, str) or not filename.strip():
            continue
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            continue
        key = (filename, page, raw.get("block_id"), quote)
        if key in seen:
            continue
        seen.add(key)
        evidence_id = f"E{len(prepared) + 1}"
        # Preserve viewer-specific parameters but refresh source and local ID.
        supplied_url = raw.get("viewer_url", "")
        url = urlsplit(supplied_url) if isinstance(supplied_url, str) else urlsplit("")
        extras = []
        if url.path == "/viewer" and not url.scheme and not url.netloc:
            extras = [(k, v) for k, v in parse_qsl(url.query) if k not in {"file", "page", "evidence"}]
        query = urlencode([("file", filename), ("page", page), ("evidence", evidence_id)] + extras)
        item = {
            "evidence_id": evidence_id,
            "slide_id": raw.get("slide_id"),
            "block_id": raw.get("block_id"),
            "filename": filename,
            "page_number": page,
            "quote": quote,
            "bbox": _bbox(raw.get("bbox")),
            "viewer_url": urlunsplit(("", "", "/viewer", query, "")),
        }
        prepared.append(item)
    return prepared


class QAService:
    def __init__(self, *, generator: AnswerGenerator | None = None) -> None:
        self.generator = generator if generator is not None else AnswerGenerator()

    @staticmethod
    def _extractive(evidence: list[dict[str, Any]]) -> dict[str, Any]:
        selected = evidence[:3]
        answer = "Các đoạn liên quan được tìm thấy trong bài giảng:\n\n" + "\n\n".join(
            f"{item['quote']} [{item['evidence_id']}]" for item in selected
        )
        return {"answer": answer, "citations": selected}

    def answer(
        self, question: str, evidence: Sequence[Mapping[str, Any]]
    ) -> dict[str, Any]:
        if not isinstance(question, str) or not question.strip():
            return {"answer": INSUFFICIENT_EVIDENCE, "citations": []}
        sources = prepare_evidence(evidence or [])
        if not sources:
            return {"answer": INSUFFICIENT_EVIDENCE, "citations": []}
        if not self.generator.available:
            return self._extractive(sources)
        try:
            generated = self.generator.generate(build_prompt(question, sources))
        except Exception as exc:
            # Never log exception messages: providers may include credentials/input.
            logger.warning("LLM unavailable (%s); using extractive answer", type(exc).__name__)
            return self._extractive(sources)
        if not generated:
            return self._extractive(sources)
        if generated.strip() == INSUFFICIENT_EVIDENCE:
            return {"answer": INSUFFICIENT_EVIDENCE, "citations": []}
        by_id = {item["evidence_id"]: item for item in sources}
        def sanitize(match: re.Match[str]) -> str:
            token = match.group(0)
            return token if _VALID_ID.fullmatch(token) and token[1:-1] in by_id else ""
        answer = _CITATION.sub(sanitize, generated).strip()
        cited_ids = list(dict.fromkeys(token[1:-1] for token in _VALID_ID.findall(answer)))
        if not cited_ids:
            return self._extractive(sources)
        return {"answer": answer, "citations": [by_id[key] for key in cited_ids]}

    @staticmethod
    def _extractive_mindmap(topic: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
        nodes = [
            {
                "label": item["quote"][:70] + ("…" if len(item["quote"]) > 70 else ""),
                "filename": item["filename"],
                "page_number": item["page_number"],
                "bbox": item["bbox"],
                "viewer_url": item["viewer_url"],
            }
            for item in sources[:_MAX_MINDMAP_NODES_PER_BRANCH]
        ]
        return {"title": topic, "branches": [{"label": "Nội dung liên quan", "nodes": nodes}] if nodes else []}

    @staticmethod
    def _parse_mindmap_branches(generated: str, sources: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
        text = _CODE_FENCE.sub("", generated.strip()).strip()
        try:
            payload = json.loads(text)
        except (ValueError, TypeError):
            return None
        if not isinstance(payload, dict) or not isinstance(payload.get("branches"), list):
            return None
        by_id = {item["evidence_id"]: item for item in sources}
        branches = []
        for raw_branch in payload["branches"][:_MAX_MINDMAP_BRANCHES]:
            if not isinstance(raw_branch, dict):
                continue
            label = raw_branch.get("label")
            children = raw_branch.get("children")
            if not isinstance(label, str) or not label.strip() or not isinstance(children, list):
                continue
            nodes = []
            for child in children[:_MAX_MINDMAP_NODES_PER_BRANCH]:
                if not isinstance(child, dict):
                    continue
                child_label = child.get("label")
                source = by_id.get(child.get("evidence_id"))
                if not isinstance(child_label, str) or not child_label.strip() or source is None:
                    continue
                nodes.append({
                    "label": child_label.strip()[:80],
                    "filename": source["filename"],
                    "page_number": source["page_number"],
                    "bbox": source["bbox"],
                    "viewer_url": source["viewer_url"],
                })
            if nodes:
                branches.append({"label": label.strip()[:40], "nodes": nodes})
        return branches

    def mindmap(self, topic: str, evidence: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        if not isinstance(topic, str) or not topic.strip():
            return {"title": topic, "branches": []}
        sources = prepare_evidence(evidence or [])
        if not sources:
            return {"title": topic, "branches": []}
        if not self.generator.available:
            return self._extractive_mindmap(topic, sources)
        try:
            generated = self.generator.generate(
                build_mindmap_prompt(topic, sources), instructions=MINDMAP_SYSTEM_PROMPT
            )
        except Exception as exc:
            # Never log exception messages: providers may include credentials/input.
            logger.warning("LLM unavailable (%s); using extractive mindmap", type(exc).__name__)
            return self._extractive_mindmap(topic, sources)
        branches = self._parse_mindmap_branches(generated, sources) if generated else None
        if not branches:
            return self._extractive_mindmap(topic, sources)
        return {"title": topic, "branches": branches}

    def organize_mindmap(self, day_label: str, nodes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]] | None:
        """Ask the LLM to summarize already-extracted, real slide headings into a topic overview.

        Unlike `mindmap()`, the model never invents a label or a source here —
        it only picks which existing index goes under which branch — so a bad
        response can mis-group or omit real content but can never fabricate
        it. This is a representative overview, not an index of every slide:
        the model is asked to keep only each branch's most representative
        items, so most indices are expected to go unused rather than all
        being force-fit into a branch. Returns None (caller falls back to
        rule-based grouping) on any unavailable/malformed response.
        """
        nodes = list(nodes)
        if not nodes or not self.generator.available:
            return None
        capped = nodes[:_MAX_ORGANIZE_NODES]
        try:
            generated = self.generator.generate(
                build_organize_prompt(day_label, capped), instructions=ORGANIZE_SYSTEM_PROMPT
            )
        except Exception as exc:
            logger.warning("LLM unavailable (%s); using rule-based mindmap grouping", type(exc).__name__)
            return None
        if not generated:
            return None
        text = _CODE_FENCE.sub("", generated.strip()).strip()
        try:
            payload = json.loads(text)
        except (ValueError, TypeError):
            return None
        if not isinstance(payload, dict) or not isinstance(payload.get("branches"), list):
            return None
        used: set[int] = set()
        branches = []
        for raw_branch in payload["branches"][:_MAX_MINDMAP_BRANCHES]:
            if not isinstance(raw_branch, dict):
                continue
            label = raw_branch.get("label")
            indices = raw_branch.get("indices")
            if not isinstance(label, str) or not label.strip() or not isinstance(indices, list):
                continue
            branch_nodes = []
            for index in indices:
                if len(branch_nodes) >= _MAX_ORGANIZE_NODES_PER_BRANCH:
                    break  # a representative overview, not a full index — see prompt rule 3
                if not isinstance(index, int) or isinstance(index, bool) or index in used:
                    continue
                if not (0 <= index < len(capped)):
                    continue
                used.add(index)
                branch_nodes.append(capped[index])
            if branch_nodes:
                branches.append({"label": label.strip()[:40], "nodes": branch_nodes})
        return branches or None
