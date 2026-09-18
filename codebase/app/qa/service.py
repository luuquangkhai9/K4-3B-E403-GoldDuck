"""Frozen QAService interface with deterministic source metadata."""

import json
import logging
import math
import os
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.viewer.evidence import normalized_bbox
from app.ingestion.metadata import record_day_metadata
from app.retrieval.query import is_document_discovery
from app.ingestion.metadata import normalize_scope
from .intent import parse_explicit_mindmap_scope

from .generator import AnswerGenerator
from .prompts import (
    INSUFFICIENT_EVIDENCE, INTENT_SYSTEM_PROMPT, MINDMAP_SYSTEM_PROMPT,
    ORGANIZE_SYSTEM_PROMPT, build_intent_prompt, build_mindmap_prompt,
    build_organize_prompt, build_prompt,
)

logger = logging.getLogger(__name__)
_CITATION = re.compile(r"\[\s*E[^\[\]\n]*\]", re.IGNORECASE)
_VALID_ID = re.compile(r"\[E[1-9]\d*\]")

_CODE_FENCE = re.compile(r"^```[a-zA-Z]*\n?|```$")
_MAX_MINDMAP_BRANCHES = 8
_MAX_MINDMAP_NODES_PER_BRANCH = 10
_MAX_ORGANIZE_NODES_PER_BRANCH = 6  # a representative overview, not every slide — see ORGANIZE_SYSTEM_PROMPT
# Items are short label strings, so even a generous cap is cheap in tokens.
# A lesson bundling many near-duplicate presenter decks can genuinely have a
# few hundred deduplicated headings (observed: 379) — this just needs to stay
# above that so the model sees the whole day's material to pick from, not
# because every item needs to end up in the output (it won't; see above).
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
        block_id = raw.get("block_id")
        if block_id is not None and not isinstance(block_id, str):
            continue
        try:
            learning_day = record_day_metadata(raw)
        except ValueError:
            continue
        key = (filename, page, block_id, quote)
        if key in seen:
            continue
        seen.add(key)
        evidence_id = f"E{len(prepared) + 1}"
        # Preserve viewer-specific parameters but refresh source and local ID.
        supplied_url = raw.get("viewer_url", "")
        try:
            url = urlsplit(supplied_url) if isinstance(supplied_url, str) else urlsplit("")
        except ValueError:
            url = urlsplit("")
        extras = []
        if url.path == "/viewer" and not url.scheme and not url.netloc:
            extras = [(k, v) for k, v in parse_qsl(url.query) if k not in {"file", "page", "evidence", "bbox"}]
        bbox = normalized_bbox(raw.get("bbox"))
        if bbox is not None:
            extras.append(("bbox", ",".join(str(v) for v in bbox)))
        query = urlencode([("file", filename), ("page", page), ("evidence", evidence_id)] + extras)
        item = {
            "evidence_id": evidence_id,
            "slide_id": raw.get("slide_id"),
            "block_id": block_id,
            "filename": filename,
            "document_id": raw.get("document_id"),
            **learning_day,
            "page_number": page,
            "quote": quote,
            "bbox": bbox,
            "viewer_url": urlunsplit(("", "", "/viewer", query, "")),
            "source_role": "neighbor" if raw.get("source_role") == "neighbor" else "primary",
            "evidence_type": "visual" if raw.get("evidence_type") == "visual" else "native",
            "vision_used": raw.get("vision_used") is True,
        }
        score = raw.get("block_score")
        if isinstance(score, (int, float)) and not isinstance(score, bool):
            try:
                if math.isfinite(score):
                    item["block_score"] = float(score)
            except OverflowError:
                pass
        prepared.append(item)
    return prepared


class QAService:
    def __init__(self, *, generator: AnswerGenerator | None = None) -> None:
        self.generator = generator if generator is not None else AnswerGenerator()
        self.no_answer_enabled = os.getenv("NO_ANSWER_ENABLED", "true").strip().lower() not in {"false", "0", "no", "off"}
        self.citation_validation_enabled = os.getenv("CITATION_VALIDATION_ENABLED", "true").strip().lower() not in {"false", "0", "no", "off"}
        try:
            threshold = float(os.getenv("NO_ANSWER_THRESHOLD", ""))
            self.no_answer_threshold = threshold if math.isfinite(threshold) else None
        except ValueError:
            self.no_answer_threshold = None

    @staticmethod
    def _result(answer, citations, *, removed=(), no_answer=False, regenerated=False, fallback=False):
        return {
            "answer": answer,
            "citations": citations,
            "grounding": {
                "status": "insufficient_evidence" if no_answer else "grounded",
                "used_evidence_ids": [item["evidence_id"] for item in citations],
                "invalid_citations_removed": list(dict.fromkeys(removed)),
                "no_answer": no_answer,
                "regenerated": regenerated,
                "extractive_fallback": fallback,
            },
        }

    @staticmethod
    def _extractive(evidence: list[dict[str, Any]], question="") -> dict[str, Any]:
        if is_document_discovery(question):
            selected = []
            seen = set()
            for item in sorted(evidence, key=lambda item: item["source_role"] == "neighbor"):
                if item["filename"] not in seen:
                    seen.add(item["filename"])
                    selected.append(item)
            answer = "Các tài liệu liên quan được tìm thấy:\n\n" + "\n\n".join(
                f"{item['filename']} — {item.get('day_label') or 'chưa xác định ngày học'}: "
                f"{_CITATION.sub('', item['quote'])} [{item['evidence_id']}]" for item in selected
            )
            return QAService._result(answer, selected, fallback=True)
        selected = sorted(evidence, key=lambda item: item["source_role"] == "neighbor")[:3]
        answer = "Các đoạn liên quan được tìm thấy trong bài giảng:\n\n" + "\n\n".join(
            f"{_CITATION.sub('', item['quote'])} [{item['evidence_id']}]" for item in selected
        )
        return QAService._result(answer, selected, fallback=True)

    def answer(
        self, question: str, evidence: Sequence[Mapping[str, Any]]
    ) -> dict[str, Any]:
        if not isinstance(question, str) or not question.strip():
            return self._result(INSUFFICIENT_EVIDENCE, [], no_answer=True)
        sources = prepare_evidence(evidence or [])
        if not sources:
            return self._result(INSUFFICIENT_EVIDENCE, [], no_answer=True)
        scores = [item["block_score"] for item in sources if "block_score" in item]
        if self.no_answer_enabled and self.no_answer_threshold is not None and scores and max(scores) < self.no_answer_threshold:
            return self._result(INSUFFICIENT_EVIDENCE, [], no_answer=True)
        if not self.generator.available:
            return self._extractive(sources, question)
        by_id = {item["evidence_id"]: item for item in sources}
        removed = []
        prompt = build_prompt(question, sources)
        regenerated = False
        for attempt in range(2 if self.citation_validation_enabled else 1):
            regenerated = bool(attempt)
            try:
                generated = self.generator.generate(prompt)
            except Exception as exc:
                # Provider errors may contain credentials or source text.
                logger.warning("LLM unavailable (%s); using extractive answer", type(exc).__name__)
                break
            if not isinstance(generated, str) or not generated.strip():
                break
            if generated.strip() == INSUFFICIENT_EVIDENCE:
                return self._result(INSUFFICIENT_EVIDENCE, [], removed=removed, no_answer=True, regenerated=regenerated)
            invalid = []
            valid_count = 0
            def sanitize(match: re.Match[str]) -> str:
                nonlocal valid_count
                token = match.group(0)
                if _VALID_ID.fullmatch(token) and token[1:-1] in by_id:
                    valid_count += 1
                    return token
                invalid.append(token[1:-1].strip())
                return ""
            answer = _CITATION.sub(sanitize, generated).strip()
            removed.extend(invalid)
            if answer == INSUFFICIENT_EVIDENCE:
                return self._result(INSUFFICIENT_EVIDENCE, [], removed=removed, no_answer=True, regenerated=regenerated)
            cited_ids = list(dict.fromkeys(token[1:-1] for token in _VALID_ID.findall(answer)))
            if cited_ids and (not self.citation_validation_enabled or len(invalid) <= valid_count):
                return self._result(answer, [by_id[key] for key in cited_ids], removed=removed, regenerated=regenerated)
            prompt = build_prompt(question, sources) + (
                "\nCORRECTION: Cite every important factual claim using only the provided "
                "[E1]..[En] IDs. If the evidence is insufficient, return the required abstention sentence."
            )
        result = self._extractive(sources, question)
        result["grounding"].update(invalid_citations_removed=list(dict.fromkeys(removed)), regenerated=regenerated)
        return result

    @staticmethod
    def _mindmap_source(item):
        return {key: item.get(key) for key in (
            "evidence_id", "slide_id", "block_id", "document_id", "filename", "page_number",
            "quote", "bbox", "viewer_url", "day_id", "day_number", "day_label", "evidence_type", "vision_used",
        )}

    @staticmethod
    def _extractive_mindmap(topic: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
        nodes = [
            {
                "label": item["quote"][:70] + ("…" if len(item["quote"]) > 70 else ""),
                **QAService._mindmap_source(item),
            }
            for item in sources[:_MAX_MINDMAP_NODES_PER_BRANCH]
        ]
        return {"title": topic, "branches": [{"label": "Nội dung liên quan", "nodes": nodes}] if nodes else []}

    @staticmethod
    def _parse_mindmap_branches(generated: str, sources: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
        if not isinstance(generated, str):
            return None
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
                evidence_id = child.get("evidence_id")
                source = by_id.get(evidence_id) if isinstance(evidence_id, str) else None
                if not isinstance(child_label, str) or not child_label.strip() or source is None:
                    continue
                nodes.append({
                    "label": child_label.strip()[:80],
                    **QAService._mindmap_source(source),
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
        scores = [item["block_score"] for item in sources if "block_score" in item]
        if self.no_answer_enabled and self.no_answer_threshold is not None and scores and max(scores) < self.no_answer_threshold:
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
        if branches is None:
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
        if not isinstance(generated, str) or not generated.strip():
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

    @staticmethod
    def _sample_nodes(nodes, limit):
        if len(nodes) <= limit:
            return list(nodes)
        if limit == 1:
            return [nodes[0]]
        return [nodes[round(index * (len(nodes) - 1) / (limit - 1))] for index in range(limit)]

    def overview_mindmap(self, days):
        """One model call, balanced input, and at least one branch per selected day."""
        scope = [day for day, _ in days]
        pool = []
        originals = {}
        limit = min(40, max(1, _MAX_ORGANIZE_NODES // max(1, len(days))))
        for day, nodes in days:
            for node in self._sample_nodes(nodes, limit):
                originals[node["slide_id"]] = node
                pool.append({**node, "label": f"{day}: {node['label']}"})
        title = " · ".join(f"Day {int(day[3:]):02d}" for day in scope)
        organized = self.organize_mindmap(title, pool) if pool else None
        selected = {}
        for branch in organized or []:
            for candidate in branch["nodes"]:
                node = originals.get(candidate.get("slide_id"))
                if node is not None:
                    selected.setdefault(node["day_id"], {})[node["slide_id"]] = node
        branches = []
        for day, nodes in days:
            representatives = list(selected.get(day, {}).values()) or self._sample_nodes(nodes, 6)
            if representatives:
                branches.append({"label": f"Day {int(day[3:]):02d}",
                                 "nodes": self._sample_nodes(representatives, 6)})
        return {"title": title, "scope": scope, "branches": branches}

    def extract_mindmap_intent(self, message: str, available_days: Sequence[str]) -> dict[str, Any] | None:
        """Ask the LLM which day and/or topic a chat message wants a mindmap for.

        Regex-based keyword stripping breaks on any phrasing it wasn't
        written for (a new way to say "day 7", a whole rambling question
        instead of a short topic) — the model instead reads the message like
        a person would. `day` is constrained to a real value from
        `available_days` (or null); it can never invent one. Returns None
        (caller falls back to its own regex parsing) when the model is
        unavailable or replies with something unusable.
        """
        explicit = parse_explicit_mindmap_scope(message)
        if explicit is not None:
            return explicit
        if not isinstance(message, str) or not message.strip() or not self.generator.available:
            return None
        try:
            generated = self.generator.generate(
                build_intent_prompt(message, available_days), instructions=INTENT_SYSTEM_PROMPT
            )
        except Exception as exc:
            logger.warning("LLM unavailable (%s); using regex mindmap intent parsing", type(exc).__name__)
            return None
        if not isinstance(generated, str) or not generated.strip():
            return None
        text = _CODE_FENCE.sub("", generated.strip()).strip()
        try:
            payload = json.loads(text)
        except (ValueError, TypeError):
            return None
        if not isinstance(payload, dict):
            return None
        day = payload.get("day")
        if not isinstance(day, str) or day not in available_days:
            day = None
        topic = payload.get("topic")
        topic = topic.strip()[:200] if isinstance(topic, str) and topic.strip() else None
        if payload.get("scope"):
            try:
                scope = normalize_scope(payload["scope"])
            except ValueError:
                return None
            if len(scope) > 50 or any(item not in available_days for item in scope):
                return None
            return {"day": scope[0] if len(scope) == 1 else None, "scope": scope, "topic": topic}
        if day is None and topic is None:
            return None
        return {"day": day, "topic": topic}
