"""Cohere HTTP adapter; every failure preserves the original RRF order."""
import json
import math
import os
from urllib.request import Request, urlopen

from .config import enabled, retrieval_text


def rerank(question, slides, top_k):
    debug = {"reranker_used": False, "reranker_fallback": False}
    if not enabled("RERANK_ENABLED") or not slides:
        return slides[:top_k], debug
    try:
        provider = os.getenv("RERANK_PROVIDER", "cohere").strip().lower()
        key = os.getenv("RERANK_API_KEY", "").strip()
        model = os.getenv("RERANK_MODEL", "").strip()
        if provider != "cohere" or not key or not model:
            raise ValueError("missing_or_unsupported_configuration")
        documents = []
        for slide in slides:
            visual = slide.get("visual_analysis") or {}
            summary = visual.get("summary", "") if isinstance(visual, dict) else ""
            documents.append(f"Document: {slide['filename']}\nPage: {slide['page_number']}\n"
                             + retrieval_text(slide) + "\n" + str(summary))
        request = Request("https://api.cohere.com/v2/rerank", method="POST",
                          data=json.dumps({"model": model, "query": question,
                                           "documents": documents, "top_n": min(top_k, len(slides))}).encode(),
                          headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        timeout = float(os.getenv("RERANK_TIMEOUT_SECONDS", "10"))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("invalid_timeout")
        with urlopen(request, timeout=timeout) as response:
            results = json.load(response)["results"]
        if not isinstance(results, list) or len(results) != min(top_k, len(slides)):
            raise ValueError("incomplete_response")
        ordered, seen = [], set()
        for result in results:
            index = result["index"]
            score = result["relevance_score"]
            if (type(index) is not int or not 0 <= index < len(slides) or index in seen
                    or isinstance(score, bool) or not isinstance(score, (int, float))
                    or not math.isfinite(score) or not 0 <= score <= 1):
                raise ValueError("invalid_response")
            seen.add(index)
            ordered.append(dict(slides[index], rerank_score=float(score)))
        debug["reranker_used"] = True
        return ordered, debug
    except Exception:
        # Do not log provider bodies or credentials.
        debug["reranker_fallback"] = True
        return slides[:top_k], debug
