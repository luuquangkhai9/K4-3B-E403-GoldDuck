Agent 1:
- pymupdf

Agent 2:
- numpy
- rank-bm25
- sentence-transformers


Agent 3:
- openai (SDK cho LLM; extractive fallback không cần dependency)

Agent 4 — consolidation:
- All requests above are already included in requirements.txt.
- httpx added for API integration tests and HTTP provider adapters; no extra provider SDK required.


Agent 3 - V2 QA hardening: no additional dependencies requested; uses the existing OpenAI adapter and Python standard library.

## Agent 1 — Selective Vision ingestion
- No new dependencies: uses existing PyMuPDF and Python standard-library HTTP client.
- Configuration consumed: VISION_ENABLED (default false), VISION_PROVIDER (openai or openai-compatible), VISION_MODEL (required when enabled), VISION_API_KEY (falls back to OPENAI_API_KEY), VISION_TEXT_THRESHOLD (120), VISION_IMAGE_RATIO_THRESHOLD (0.40).
- Optional configuration: VISION_TIMEOUT (30 seconds), VISION_BASE_URL (https://api.openai.com/v1).
- Cache location: <index directory>/vision/*.json. Cache identity includes slide ID, rendered image hash, provider, model, endpoint, native text hash, and prompt.
- Tests: python -m unittest app.ingestion.test_ingestion app.ingestion.test_vision -v (13 passing).
- Real paid Vision API call not exercised; configure credentials and a model supporting images and strict JSON schema for the live smoke test.

Agent 2 V2:
- No new dependencies. Cohere reranker uses Python urllib; block ranking reuses numpy and sentence-transformers.
- Integration config: RERANK_ENABLED, RERANK_PROVIDER=cohere, RERANK_API_KEY, RERANK_MODEL (required), RERANK_CANDIDATES=20, RERANK_TOP_K=5, optional RERANK_TIMEOUT_SECONDS=10; NEIGHBOR_EXPANSION_ENABLED, NEIGHBOR_DISTANCE=1; EVIDENCE_TOP_K=5, MAX_EVIDENCE_PER_SLIDE=2.
