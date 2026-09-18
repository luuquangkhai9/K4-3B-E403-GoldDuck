# HACKATHON V2 IMPLEMENTATION PLAN
## Multimodal Upgrade for Grounded Lecture QA

**Context:** V1 is already implemented and tested successfully.  
**Machine:** CPU-only, no GPU.  
**Allowed:** Paid APIs may be used.  
**Team:** 4 coding agents working in parallel in the SAME project directory.  
**Goal:** Upgrade retrieval, visual understanding, evidence quality, and grounding without breaking V1.

---

# 0. Core Rule

V1 works. V2 must be additive and backward-compatible.

Every V2 component must fail safely back to the V1 path:

```text
PDF
 -> PyMuPDF
 -> BM25 + multilingual-e5-small
 -> RRF
 -> Evidence
 -> Grounded QA
 -> Citation
```

Do not rewrite working V1 architecture.

---

# 1. V2 Scope

Implement only these upgrades:

1. Selective Vision API for image-heavy / low-text slides.
2. External API reranking after BM25 + E5 + RRF.
3. Neighbor-slide expansion (`±1` by default).
4. Block-level evidence ranking.
5. No-answer guard.
6. Citation validation.
7. UI/API integration and debug visibility.

Do NOT implement:

- local VLMs / ColPali / ColQwen
- GraphRAG
- knowledge graph
- Elasticsearch/Qdrant migration
- microservices
- fine-tuning
- full benchmark framework
- major OCR rewrite
- Kubernetes / queues / auth

---

# 2. Target Architecture

```text
                         OFFLINE / INDEXING

PDF
 |
 v
PyMuPDF
 |
 +--> text
 +--> blocks + bbox
 +--> images/layout
 |
 v
Visual Necessity Detector
 |
 +--> enough native text -----------------------------+
 |                                                   |
 +--> image-heavy / low-text                         |
                  |                                  |
                  v                                  |
              Vision API                            |
                  |                                  |
     summary + concepts + relationships              |
                  |                                  |
                  +---------------+------------------+
                                  |
                                  v
                         retrieval_text
                                  |
                                  v
                         E5-small embedding
                                  |
                                  v
                                cache


                         ONLINE / QUERY

Question
   |                 |
   v                 v
 BM25             E5-small
   |                 |
   +--------+--------+
            |
            v
           RRF
            |
          Top 20
            |
            v
      API Reranker
            |
           Top 5
            |
            v
   Neighbor Expansion ±1
            |
            v
    Block Evidence Ranking
            |
          E1..E5
            |
            v
      Grounded LLM
            |
            v
     Citation Validation
            |
            v
      No-answer Guard
            |
            v
Answer + PDF + page + quote + bbox
```

---

# 3. Compatibility Requirements

Keep these V1 interfaces unchanged.

## Retrieval

```python
from app.retrieval.service import RetrievalService

result = RetrievalService().retrieve(
    question="...",
    top_k=5
)
```

Mandatory response keys:

```python
{
    "slides": [...],
    "evidence": [...]
}
```

V2 may add more keys.

## QA

```python
from app.qa.service import QAService

result = QAService().answer(
    question="...",
    evidence=[...]
)
```

Mandatory:

```python
{
    "answer": "...",
    "citations": [...]
}
```

---

# 4. Extended Slide Schema

Add optional fields only. Do not remove V1 fields.

```python
{
    "slide_id": "doc_001_p0007",
    "document_id": "doc_001",
    "filename": "lecture_01.pdf",
    "page_index": 6,
    "page_number": 7,

    "text": "...",
    "blocks": [...],

    "visual_analysis": {
        "needed": True,
        "reason": "low_text_high_image",
        "status": "success",
        "summary": "Slide mô tả kiến trúc CNN...",
        "concepts": ["CNN", "convolution", "pooling"],
        "relationships": ["Input -> Convolution -> Pooling"],
        "visible_text_not_in_pdf": [],
        "provider": "<configured-provider>",
        "model": "<configured-model>",
        "cached": True
    },

    "retrieval_text":
      "native text + visual summary + concepts + relationships"
}
```

If Vision is not needed:

```python
"visual_analysis": {
    "needed": False,
    "reason": "sufficient_native_text",
    "status": "skipped"
}
```

---

# 5. V2 Evidence Schema

```python
{
    "evidence_id": "E1",
    "slide_id": "doc_001_p0007",
    "block_id": "doc_001_p0007_b002",

    "filename": "lecture_01.pdf",
    "page_number": 7,

    "quote": "...",
    "bbox": [0.11, 0.43, 0.87, 0.56],

    "block_score": 0.91,

    "source_role": "primary",

    "viewer_url":
      "/viewer?file=lecture_01.pdf&page=7&evidence=E1"
}
```

Neighbor source:

```python
"source_role": "neighbor"
```

---

# 6. Environment Configuration

Add configuration, never hardcode model IDs in business logic.

```text
# Existing
OPENAI_API_KEY=
LLM_MODEL=
DENSE_ENABLED=true
TOP_K=5

# Vision
VISION_ENABLED=true
VISION_PROVIDER=openai
VISION_MODEL=
VISION_TEXT_THRESHOLD=120
VISION_IMAGE_RATIO_THRESHOLD=0.40

# Reranker
RERANK_ENABLED=true
RERANK_PROVIDER=cohere
RERANK_API_KEY=
RERANK_MODEL=
RERANK_CANDIDATES=20
RERANK_TOP_K=5

# Neighbor
NEIGHBOR_EXPANSION_ENABLED=true
NEIGHBOR_DISTANCE=1

# Evidence
EVIDENCE_TOP_K=5
MAX_EVIDENCE_PER_SLIDE=2

# Grounding
NO_ANSWER_ENABLED=true
NO_ANSWER_THRESHOLD=
CITATION_VALIDATION_ENABLED=true
```

---

# 7. Selective Vision Design

Because there is no local GPU:

> Vision is API-only and ingestion-time only.

Never call Vision API on every user query.

## Visual Necessity Heuristic

A slide requires Vision when ANY condition is true:

```python
len(native_text.strip()) < VISION_TEXT_THRESHOLD
```

or:

```python
image_area_ratio >= VISION_IMAGE_RATIO_THRESHOLD
```

or:

```text
large image + low text density
```

Keep this deterministic and simple.

## Vision Input

Render only flagged slides using PyMuPDF.

Recommended width:

```text
1280-1600 px
```

## Vision Output

Force structured JSON:

```json
{
  "summary": "Slide mô tả...",
  "concepts": ["..."],
  "relationships": ["A -> B"],
  "visible_text_not_in_pdf": ["..."]
}
```

Prompt principle:

```text
Describe only visible content on the lecture slide.
Do not add outside knowledge.
Do not infer facts not visually supported.
```

## Retrieval Text

```python
parts = [
    native_text,
    visual_summary,
    "Concepts: " + ", ".join(concepts),
    "Relationships: " + "; ".join(relationships),
]
retrieval_text = "\n".join(x for x in parts if x)
```

If no visual analysis:

```python
retrieval_text = native_text
```

## Cache

Cache by:

```text
slide_id + image_hash + provider + model
```

Suggested location:

```text
data/index/vision/
```

One JSON file per slide is acceptable.

Never pay twice for unchanged content.

---

# 8. API Reranker Design

Keep V1 first-stage retrieval:

```text
BM25 + E5-small + RRF
```

Then:

```text
RRF Top 20
     |
     v
API Reranker
     |
     v
Top 5
```

Reranker input for a slide should include:

```text
Document metadata
Slide text
Visual summary if available
```

Failure rules:

```text
missing key
timeout
rate limit
provider error
```

must return:

```text
original RRF ordering
```

No QA request should fail because reranking failed.

---

# 9. Neighbor Slide Expansion

After reranking:

```text
Primary Top 5
```

For each primary slide add:

```text
page - 1
page
page + 1
```

according to configured distance.

Deduplicate by `slide_id`.

Role rules:

```python
role = "primary"
```

or:

```python
role = "neighbor"
neighbor_of = "<primary-slide-id>"
distance = -1 or +1
```

Citation preference:

```text
primary evidence > equivalent neighbor evidence
```

Neighbor slides provide context; they are not automatically citations.

---

# 10. Evidence Block Ranking

Do not send all slide text to the final LLM.

Pipeline:

```text
primary + neighbor slides
        |
        v
collect text blocks
        |
        v
filter boilerplate
        |
        v
E5-small block ranking
        |
        v
Top 5 evidence blocks
```

Use:

```text
query: <question>
passage: <block text>
```

with normalized cosine similarity.

Filter meaningless blocks:

```text
page number only
copyright/footer
empty strings
very short boilerplate
```

Evidence diversity:

```text
max 2 evidence blocks per slide
```

unless configuration overrides it.

---

# 11. Grounded QA V2

Final model receives only selected evidence:

```text
QUESTION:
...

[E1]
Document: ...
Page: ...
Role: primary
Text: ...

[E2]
...
```

Required rules:

```text
1. Use only provided EVIDENCE.
2. Do not add outside knowledge.
3. Every important factual claim must cite evidence.
4. Only use provided IDs E1..En.
5. Never invent citation IDs.
6. If evidence is insufficient, say so explicitly.
7. Prefer primary-slide evidence.
8. Neighbor evidence is supplementary.
```

---

# 12. No-Answer Guard

First version should be simple.

Return no-answer when:

```text
no evidence
```

or:

```text
top block relevance < configured threshold
```

or:

```text
LLM judges evidence insufficient
```

Canonical response:

```text
Không tìm thấy đủ thông tin trong kho bài giảng để trả lời câu hỏi này.
```

Never create a plausible answer from pretrained knowledge.

---

# 13. Citation Validation

## Required validation

Extract citation IDs from the answer.

For each:

```python
if citation_id not in provided_evidence_ids:
    remove_or_regenerate
```

Invalid IDs must never reach the final API response.

## Missing citations

If the generated answer has substantive claims but zero valid citations:

```text
regenerate once
```

If still invalid:

```text
return extractive/no-answer fallback
```

Do not silently invent a citation.

## Optional claim-level validation

Only after all core V2 work is stable.

This is P2, not P0.

---

# 14. Agent Ownership

All agents share the SAME project directory.

Strict ownership is required.

---

# AGENT 1 — SELECTIVE VISION INGESTION

## Exclusive ownership

```text
app/ingestion/**
scripts/ingest.py
data/index/vision/**
data/index/vision_cache.json
DEPENDENCIES_REQUESTED.md (append-only)
```

Do not edit retrieval, QA, API, viewer, README, or requirements.

## Tasks

1. Inspect existing V1 ingestion.
2. Preserve V1 behavior.
3. Extend slide schema with optional:
   - `visual_analysis`
   - `retrieval_text`
4. Implement visual necessity detector.
5. Measure low text / image-heavy conditions.
6. Render only flagged pages.
7. Add configurable Vision API adapter.
8. Force structured JSON:
   - summary
   - concepts
   - relationships
   - visible_text_not_in_pdf
9. Prevent external-knowledge additions in prompt.
10. Cache by slide/image/model identity.
11. Reuse cached output on re-ingestion.
12. Build `retrieval_text`.
13. `VISION_ENABLED=false` must behave like V1.
14. Vision failure must not stop ingestion.

## Definition of Done

Text-heavy slide:

```text
status = skipped
no API call
```

Visual-heavy slide:

```text
status = success
visual summary exists
retrieval_text includes visual information
```

Second ingestion:

```text
cache hit
no repeated API cost
```

---

# AGENT 2 — RERANK + NEIGHBOR + BLOCK RANKING

## Exclusive ownership

```text
app/retrieval/**
data/index/embeddings.npy
data/index/retrieval_meta.json
DEPENDENCIES_REQUESTED.md (append-only)
```

Do not edit ingestion, QA, API, viewer, README, or requirements.

## Tasks

1. Preserve BM25 + E5 + RRF.
2. Use `retrieval_text` when available.
3. Fall back to `text`.
4. Add external API reranker.
5. Rerank RRF Top-N.
6. Fall back to RRF on any API failure.
7. Add configurable neighbor expansion.
8. Mark primary/neighbor roles.
9. Deduplicate expanded slides.
10. Implement block-level E5 ranking.
11. Apply evidence diversity.
12. Preserve:
   `RetrievalService.retrieve(question, top_k=5)`.
13. Preserve mandatory keys:
   `slides`, `evidence`.
14. Add optional debug metadata.

## Suggested extended output

```python
{
    "slides": [...],
    "primary_slides": [...],
    "context_slides": [...],
    "evidence": [...],

    "debug": {
        "reranker_used": True,
        "reranker_fallback": False,
        "first_stage_count": 20
    }
}
```

## Definition of Done

Reranker enabled:

```text
BM25 + E5 -> RRF -> API rerank -> Top 5
```

Reranker failure:

```text
BM25 + E5 -> RRF -> Top 5
```

still succeeds.

Evidence blocks return relevance scores.

---

# AGENT 3 — QA HARDENING

## Exclusive ownership

```text
app/qa/**
DEPENDENCIES_REQUESTED.md (append-only)
```

Do not edit ingestion, retrieval, API, viewer, README, or requirements.

## Tasks

1. Preserve `QAService.answer(question, evidence)`.
2. Accept V1 and V2 evidence.
3. Assign deterministic `E1..En`.
4. Upgrade grounding prompt.
5. Prefer primary evidence.
6. Validate every citation ID.
7. Remove invalid citation IDs.
8. Add no-answer behavior.
9. Allow maximum one regeneration when:
   - citations are missing
   - invalid citations dominate
10. Preserve extractive fallback when LLM API fails.
11. Return grounding metadata.

## Suggested output

```python
{
    "answer": "...",
    "citations": [...],

    "grounding": {
        "status": "grounded",
        "used_evidence_ids": ["E1", "E3"],
        "invalid_citations_removed": [],
        "no_answer": False
    }
}
```

Other status:

```text
insufficient_evidence
```

## Definition of Done

- No invented evidence IDs can reach API output.
- Unsupported questions can abstain.
- LLM failure still produces safe fallback.

---

# AGENT 4 — INTEGRATION / API / UI / CONFIG

## Exclusive ownership

```text
app/api/**
app/viewer/**
README.md
requirements.txt
.env.example
scripts/run_demo.py
DEPENDENCIES_REQUESTED.md
```

Do not edit ingestion, retrieval, or QA internals.

## Tasks

1. Preserve V1 API behavior.
2. Add all V2 environment variables.
3. Integrate extended retrieval output.
4. Integrate grounding metadata.
5. Keep `/api/ask` backward-compatible.
6. Update source cards to display:
   - evidence ID
   - filename
   - page
   - quote
   - primary/neighbor role
   - source link
7. Preserve bbox behavior.
8. Optionally show debug:
   - reranker used?
   - vision used on cited slide?
   - no-answer?
9. Consolidate dependencies requested by Agents 1-3.
10. Update README.
11. Preserve one-command startup.
12. Run integration with V2 disabled.
13. Run integration with V2 enabled.

---

# 15. Shared Dependency Policy

Agents 1-3 do NOT edit `requirements.txt`.

Append requests to:

```text
DEPENDENCIES_REQUESTED.md
```

Agent 4 consolidates.

Avoid installing unnecessary provider SDKs if the existing HTTP client is sufficient.

---

# 16. Integration Checkpoints

## A — V1 Compatibility

Disable:

```text
VISION_ENABLED=false
RERANK_ENABLED=false
NEIGHBOR_EXPANSION_ENABLED=false
CITATION_VALIDATION_ENABLED=false
```

Expected:

```text
V1 still works end-to-end
```

## B — Reranker

Enable reranker only.

Expected:

```text
question -> RRF -> rerank -> evidence -> answer
```

## C — Vision

Enable Vision and re-ingest.

Expected:

```text
visual-heavy slide
-> visual cache
-> retrieval_text
-> dense index
```

## D — Full V2

Expected:

```text
question
-> hybrid retrieval
-> reranking
-> neighbor context
-> block evidence
-> grounded answer
-> validated citation
```

---

# 17. Minimal Smoke Test

Do NOT build a full benchmark now.

Use only 5 manually-known questions:

```text
1. Vietnamese text-heavy slide
2. English slide queried in Vietnamese
3. Visual-heavy slide
4. Question needing neighboring context
5. Question not answerable from corpus
```

For each verify:

```text
reasonable/correct slide?
source link works?
quote supports answer?
no-answer works?
```

---

# 18. Failure Strategy

```text
Vision fails
 -> native text only

Reranker fails
 -> RRF order

Neighbor expansion fails
 -> primary slides only

Block ranking fails
 -> V1 evidence selection

LLM fails
 -> extractive fallback
```

External APIs must never make the whole system unusable.

---

# 19. Cost Control

Vision:

```text
only flagged slides
one-time ingestion
persistent cache
```

Reranker:

```text
only Top 20 candidates/query
```

Generation:

```text
only Top 3-5 evidence blocks
```

Never send full PDFs to the final answer model.

---

# 20. V2 Completion Criteria

V2 is complete when:

1. V1 works with all V2 features disabled.
2. Visual-heavy slides can get cached visual descriptions.
3. RRF Top 20 can be reranked externally.
4. Neighbor context works.
5. Evidence is ranked at block level.
6. Final QA sees only selected evidence.
7. Invalid citations are rejected.
8. Unsupported questions can abstain.
9. Exact PDF/page evidence still works.
10. Five smoke-test cases pass.

---

# 21. Priority

```text
P0  Preserve V1
P1  API reranker
P1  Selective Vision + cache
P1  Block ranking
P1  Neighbor expansion
P1  Citation validation
P1  No-answer
P2  UI debug information
P3  Claim-level validation
```

---

# 22. STARTUP PROMPT — AGENT 1

```text
You are Agent 1: Selective Vision Ingestion.

Read HACKATHON_V2_PLAN.md completely before coding.

V1 is already implemented and tested successfully.
Do not rebuild it.

You work in parallel with 3 agents in the SAME directory.

STRICT OWNERSHIP:
You may edit only:
- app/ingestion/**
- scripts/ingest.py
- data/index/vision/**
- data/index/vision_cache.json
- DEPENDENCIES_REQUESTED.md (append only)

Do NOT edit retrieval, QA, API, viewer, README, requirements.txt, or other agents' files.

TASK:
1. Preserve V1 ingestion.
2. Add optional visual_analysis and retrieval_text.
3. Implement deterministic low-text / image-heavy detection.
4. Render only flagged slides.
5. Add configurable Vision API adapter.
6. Force structured JSON:
   summary, concepts, relationships, visible_text_not_in_pdf.
7. Prompt Vision to describe only visible content and add no outside knowledge.
8. Cache by slide/image hash/provider/model.
9. Never pay twice for unchanged content.
10. Build retrieval_text from native text + visual information.
11. VISION_ENABLED=false must remain V1-compatible.
12. Vision errors must gracefully fall back to native text.
13. Assume CPU-only local hardware.

Do not add a local VLM or GPU dependency.

When complete:
- test one normal slide
- test one visual-heavy slide
- verify cache hit on second run
- report files changed
- append dependency requests
- report blockers
```

---

# 23. STARTUP PROMPT — AGENT 2

```text
You are Agent 2: Retrieval V2.

Read HACKATHON_V2_PLAN.md completely before coding.

V1 BM25 + multilingual-e5-small + RRF already works.

You work in parallel with 3 agents in the SAME directory.

STRICT OWNERSHIP:
You may edit only:
- app/retrieval/**
- data/index/embeddings.npy
- data/index/retrieval_meta.json
- DEPENDENCIES_REQUESTED.md (append only)

Do NOT edit ingestion, QA, API, viewer, README, requirements.txt, or other agents' files.

TASK:
1. Preserve RetrievalService.retrieve(question, top_k=5).
2. Use retrieval_text if available; otherwise text.
3. Preserve BM25 + E5 + RRF.
4. Add configurable external reranker.
5. Rerank RRF Top-N.
6. Fall back automatically to RRF on API failure.
7. Add neighbor expansion ± configured distance.
8. Mark primary and neighbor roles.
9. Deduplicate slides.
10. Add block-level E5 evidence ranking.
11. Apply max evidence per slide.
12. Return evidence with scores.
13. Preserve mandatory output keys:
    slides, evidence.
14. Add optional debug metadata.
15. No GPU, new vector DB, or Elasticsearch.

When complete:
- test reranker success
- test reranker failure fallback
- test neighbor expansion
- test block ranking
- test V1 compatibility
- report files changed
- append dependencies
- report blockers
```

---

# 24. STARTUP PROMPT — AGENT 3

```text
You are Agent 3: Grounded QA V2.

Read HACKATHON_V2_PLAN.md completely before coding.

V1 QAService already works.
Harden it without breaking the public interface.

You work in parallel with 3 agents in the SAME directory.

STRICT OWNERSHIP:
You may edit only:
- app/qa/**
- DEPENDENCIES_REQUESTED.md (append only)

Do NOT edit ingestion, retrieval, API, viewer, README, requirements.txt, or other agents' files.

TASK:
1. Preserve QAService.answer(question, evidence).
2. Accept V1 and V2 evidence.
3. Assign deterministic E1..En.
4. Strengthen the grounded prompt:
   - evidence only
   - cite important claims
   - prefer primary evidence
   - neighbors are supplementary
   - abstain when unsupported
5. Validate all returned citation IDs.
6. Never expose fabricated IDs.
7. Add no-answer behavior.
8. If generated answer has no valid citations, regenerate at most once.
9. Preserve extractive fallback when API fails.
10. Return optional grounding metadata.
11. Do not build a complex NLI subsystem until core V2 is stable.

When complete:
- test valid citations
- test fabricated citation removal
- test no-answer
- test API failure fallback
- test V1 compatibility
- report files changed
- append dependencies
- report blockers
```

---

# 25. STARTUP PROMPT — AGENT 4

```text
You are Agent 4: V2 Integration, API, UI, and Configuration.

Read HACKATHON_V2_PLAN.md completely before coding.

V1 already works end-to-end.
Integrate V2 without breaking the demo.

You work in parallel with 3 agents in the SAME directory.

STRICT OWNERSHIP:
You may edit only:
- app/api/**
- app/viewer/**
- README.md
- requirements.txt
- .env.example
- scripts/run_demo.py
- DEPENDENCIES_REQUESTED.md

Do NOT modify ingestion, retrieval, or QA internals.

TASK:
1. Preserve V1 API behavior.
2. Add V2 env/config values.
3. Integrate extended retrieval response.
4. Integrate QA grounding metadata.
5. Keep POST /api/ask backward-compatible.
6. Update source UI:
   citation ID, filename, page, quote,
   primary/neighbor role, open-source link.
7. Preserve bbox viewer behavior.
8. Optionally expose debug:
   reranker used, vision used, no-answer status.
9. Consolidate dependency requests.
10. Update README.
11. Preserve one-command demo startup.
12. Test with every V2 feature OFF.
13. Test with every V2 feature ON.
14. Run all five smoke-test cases.

Priority:
end-to-end correctness > UI polish.

When complete:
- report files changed
- report integration status
- report blockers
```

---

# 26. Final Coordination Rules

All agents:

```text
1. Read this plan first.
2. Respect file ownership.
3. Never rename frozen interfaces.
4. Never refactor another agent's module.
5. Add features backward-compatibly.
6. Every external API requires a fallback.
7. Never assume a GPU.
8. Keep changes small and testable.
```

---

# 27. Demo Story

Ideal V2 demo:

```text
User:
"Kiến trúc CNN trong bài gồm những thành phần nào?"

System:
- finds a visually-heavy CNN slide
- uses cached Vision description
- reranks it to the top
- expands nearby context
- selects exact evidence
- answers in Vietnamese
- cites the slide/page
- opens the original PDF evidence
```

Then:

```text
User asks something absent from the lectures.

System:
"Không tìm thấy đủ thông tin trong kho bài giảng để trả lời câu hỏi này."
```

That demonstrates:

```text
multimodal understanding
+ hybrid retrieval
+ reranking
+ context expansion
+ grounded generation
+ verifiable evidence
+ safe abstention
```
