"""Frozen QAService interface with deterministic source metadata."""

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

from .generator import AnswerGenerator
from .prompts import INSUFFICIENT_EVIDENCE, build_prompt

logger = logging.getLogger(__name__)
_CITATION = re.compile(r"\[\s*E[^\[\]\n]*\]", re.IGNORECASE)
_VALID_ID = re.compile(r"\[E[1-9]\d*\]")


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
