"""Frozen QAService interface with deterministic source metadata."""

import logging
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .generator import AnswerGenerator
from .prompts import INSUFFICIENT_EVIDENCE, build_prompt

logger = logging.getLogger(__name__)
_CITATION = re.compile(r"\[\s*E[^\[\]\n]*\]", re.IGNORECASE)
_VALID_ID = re.compile(r"\[E[1-9]\d*\]")


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
