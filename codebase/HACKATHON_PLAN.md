# HACKATHON IMPLEMENTATION PLAN
## Grounded Lecture QA over PDF Slides with Exact Evidence Links

**Time budget:** 2 hours
**Team:** 4 coding agents working in parallel in the same project directory
**Primary goal:** Deliver a working demo that answers questions from lecture-slide PDFs and returns exact evidence links to the correct PDF page, ideally with a highlighted text region.

---

# 1. Product Goal

Build a lightweight RAG system for lecture slides stored as PDFs.

Given a user question, the system must:

1. Search only within the provided lecture PDFs.
2. Retrieve the most relevant slide/page.
3. Produce a concise answer grounded in retrieved evidence.
4. Return citations containing:
   - PDF filename / document title
   - page number
   - quoted evidence
   - evidence bounding box when available
   - a clickable viewer URL
5. Avoid answering from model memory when the evidence is insufficient.

The corpus is expected to be approximately:
- 90% Vietnamese
- 10% English

The development machine has **no GPU**.

---

# 2. Hackathon Scope

## MUST HAVE

- PDF ingestion
- Text extraction from PDF pages
- Bounding-box extraction for text blocks
- Slide/page-level retrieval
- Vietnamese/English semantic retrieval
- Grounded answer generation
- Exact page citation
- Evidence quote
- Simple web UI or API demo
- CPU-compatible execution

## SHOULD HAVE

- Hybrid retrieval:
  - BM25 / lexical
  - multilingual dense embedding
- RRF fusion
- Exact bounding-box citation
- PDF page viewer with evidence highlight

## NICE TO HAVE

- OCR fallback for scanned slides
- reranker
- image/VLM understanding
- neighbor slide expansion
- citation verification

## OUT OF SCOPE FOR THE 2-HOUR BUILD

Do NOT spend time implementing:

- ColPali / ColQwen visual retrieval locally
- GraphRAG
- complex microservices
- distributed queues
- authentication
- production monitoring
- full document management
- expensive OCR over every page
- full multimodal retrieval pipeline

The hackathon baseline should prefer **simplicity, robustness, and demo quality**.

---

# 3. Recommended Architecture

```text
PDF files
   |
   v
PyMuPDF parser
   |
   +--> page text
   +--> text blocks + bounding boxes
   +--> document metadata
   |
   v
Structured slide records
   |
   +------------------+
   |                  |
   v                  v
BM25 / lexical     Dense embeddings
                   multilingual-e5-small
   |                  |
   +--------+---------+
            |
            v
           RRF
            |
            v
       Top-K slides
            |
            v
     Evidence blocks
            |
            v
      Grounded LLM
            |
            v
Answer + citations
            |
            v
Simple UI / API
```

---

# 4. Core Technical Choices

## PDF parser

Use:

```text
PyMuPDF / fitz
```

Reason:
- fast on CPU
- extracts native text
- preserves block coordinates
- easy page rendering if needed

---

## Embedding model

Default:

```text
intfloat/multilingual-e5-small
```

Reasons:
- multilingual
- works with Vietnamese and English
- relatively small
- CPU-friendly
- 384-dimensional embeddings

Use the E5 convention:

```text
query: <question>
passage: <slide text>
```

If model loading becomes too slow during the hackathon, allow a fallback to lexical-only retrieval.

---

## Lexical search

Simplest acceptable implementation:

```text
rank_bm25
```

Do NOT introduce Elasticsearch/OpenSearch unless it is already installed.

Hackathon preference:

```text
rank_bm25.BM25Okapi
```

---

## Vector index

For a small hackathon corpus, do NOT require Qdrant.

Preferred:

```text
numpy cosine similarity
```

or:

```text
faiss-cpu
```

Use NumPy first if corpus size is small.

This avoids infrastructure setup.

---

## LLM

Use an API-accessible LLM if credentials already exist.

The LLM must receive only retrieved evidence.

Required behavior:

```text
- answer only from evidence
- cite evidence IDs
- do not invent citations
- if evidence is insufficient, say so
```

If no API key is available, retrieval + extractive answer mode is acceptable for the demo.

---

# 5. Project Structure

All four agents MUST respect the following ownership boundaries.

```text
project/
|
|-- app/
|   |
|   |-- ingestion/
|   |   |-- parser.py
|   |   |-- models.py
|   |   `-- ingest.py
|   |
|   |-- retrieval/
|   |   |-- bm25.py
|   |   |-- dense.py
|   |   |-- fusion.py
|   |   `-- service.py
|   |
|   |-- qa/
|   |   |-- prompts.py
|   |   |-- generator.py
|   |   `-- service.py
|   |
|   |-- api/
|   |   |-- main.py
|   |   `-- schemas.py
|   |
|   `-- viewer/
|       |-- evidence.py
|       `-- static/
|
|-- data/
|   |-- pdf/
|   `-- index/
|
|-- scripts/
|   |-- ingest.py
|   `-- run_demo.py
|
|-- tests/
|
|-- requirements.txt
|-- .env.example
|-- README.md
`-- HACKATHON_PLAN.md
```

---

# 6. Shared Data Contracts

All agents MUST use these contracts.

Do not independently invent incompatible schemas.

## Document

```python
{
    "document_id": "doc_001",
    "filename": "lecture_01.pdf",
    "title": "lecture_01",
    "path": "data/pdf/lecture_01.pdf",
    "total_pages": 42
}
```

---

## SlideRecord

```python
{
    "slide_id": "doc_001_p0007",
    "document_id": "doc_001",
    "filename": "lecture_01.pdf",
    "page_index": 6,
    "page_number": 7,

    "text": "full slide text",

    "blocks": [
        {
            "block_id": "doc_001_p0007_b000",
            "text": "some evidence text",
            "bbox": [x0, y0, x1, y1]
        }
    ]
}
```

Bounding boxes may initially use PDF coordinates.

If frontend highlighting is implemented, normalize them before sending to the client:

```python
[
    x0 / page_width,
    y0 / page_height,
    x1 / page_width,
    y1 / page_height
]
```

---

## RetrievalHit

```python
{
    "slide_id": "doc_001_p0007",
    "score": 0.91,
    "rank": 1,
    "filename": "lecture_01.pdf",
    "page_number": 7,
    "text": "...",
    "blocks": [...]
}
```

---

## Evidence

```python
{
    "evidence_id": "E1",
    "slide_id": "doc_001_p0007",
    "block_id": "doc_001_p0007_b002",
    "filename": "lecture_01.pdf",
    "page_number": 7,
    "quote": "exact evidence text",
    "bbox": [0.11, 0.43, 0.87, 0.56],
    "viewer_url": "/viewer?file=lecture_01.pdf&page=7&evidence=E1"
}
```

---

## QA Response

```python
{
    "answer": "Câu trả lời có trích dẫn [E1].",
    "citations": [
        {
            "evidence_id": "E1",
            "filename": "lecture_01.pdf",
            "page_number": 7,
            "quote": "...",
            "bbox": [...],
            "viewer_url": "..."
        }
    ]
}
```

---

# 7. Retrieval Strategy

## Dense retrieval

For every slide:

```python
passage_text = f"passage: {slide['text']}"
```

For the question:

```python
query_text = f"query: {question}"
```

Embed both using:

```text
intfloat/multilingual-e5-small
```

Normalize embeddings and calculate cosine similarity.

---

## BM25

Use slide text as the lexical corpus.

For speed, simple tokenization is acceptable:

```python
text.lower().split()
```

If time permits, add Vietnamese normalization.

Do NOT spend the hackathon integrating VnCoreNLP unless retrieval quality clearly requires it.

---

## Fusion

Use Reciprocal Rank Fusion:

```python
score = sum(1 / (60 + rank))
```

Recommended:

```text
BM25 top 20
Dense top 20
RRF
Top 5 final slides
```

---

# 8. Evidence Selection

Once Top-K slides are retrieved, select evidence blocks.

For MVP:

1. Get blocks from the top 3 slides.
2. Score each block against the question.
3. Use either:
   - dense embedding similarity, OR
   - lexical overlap
4. Select the best 3-5 blocks.
5. Assign deterministic IDs:

```text
E1
E2
E3
```

Important:

The LLM is NOT allowed to invent source names or page numbers.

It may only refer to:

```text
[E1]
[E2]
...
```

The backend maps these IDs to real metadata.

---

# 9. Grounded Prompt

Use a prompt similar to:

```text
Bạn là trợ lý hỏi đáp cho kho slide bài giảng.

QUY TẮC:
1. Chỉ sử dụng thông tin trong phần EVIDENCE.
2. Không sử dụng kiến thức bên ngoài để bổ sung.
3. Mọi kết luận quan trọng phải có citation dạng [E1], [E2], ...
4. Không tự tạo citation.
5. Nếu evidence không đủ để trả lời, nói rõ:
   "Không tìm thấy đủ thông tin trong kho bài giảng để trả lời câu hỏi này."
6. Trả lời bằng tiếng Việt, trừ khi người dùng yêu cầu ngôn ngữ khác.

EVIDENCE:

[E1]
Document: ...
Page: ...
Text: ...

[E2]
...

QUESTION:
...

ANSWER:
```

---

# 10. API Contract

## POST `/api/ask`

Request:

```json
{
  "question": "Gradient descent là gì?"
}
```

Response:

```json
{
  "answer": "Gradient descent là ... [E1]",
  "citations": [
    {
      "evidence_id": "E1",
      "filename": "lecture_01.pdf",
      "page_number": 18,
      "quote": "...",
      "bbox": [0.1, 0.2, 0.9, 0.4],
      "viewer_url": "/viewer?file=lecture_01.pdf&page=18&evidence=E1"
    }
  ]
}
```

---

## POST `/api/ingest`

Optional.

For the hackathon it is acceptable to ingest using a script instead:

```bash
python scripts/ingest.py
```

---

## GET `/api/health`

Returns:

```json
{
  "status": "ok"
}
```

---

# 11. UI Requirements

The UI should be minimal.

Must show:

```text
[ Question input ]

[ Ask ]

Answer:
...

Sources:
[1] lecture_01.pdf - Slide 18
    "quoted evidence..."
    [Open source]
```

Clicking `Open source` should:

MVP:
- open PDF at the correct page

Better:
- open page and draw a highlight over the evidence bbox

Do NOT spend excessive time styling.

---

# 12. Agent Ownership

Because all agents share the SAME DIRECTORY, strict ownership is mandatory.

Agents must not edit files owned by another agent unless explicitly coordinated.

---

# AGENT 1 — PDF INGESTION & DATA MODEL

## Ownership

Agent 1 exclusively owns:

```text
app/ingestion/**
scripts/ingest.py
data/index/slides.json
```

## Tasks

1. Implement PDF discovery from:

```text
data/pdf/
```

2. Parse PDFs using PyMuPDF.
3. Extract per-page:
   - page number
   - full text
   - text blocks
   - bounding boxes
   - page width / height
4. Normalize bbox to `[0,1]`.
5. Produce `SlideRecord`.
6. Save all slide records to:

```text
data/index/slides.json
```

7. Make ingestion idempotent enough for repeated execution.
8. Add basic error handling.

## Definition of done

This command works:

```bash
python scripts/ingest.py
```

and produces:

```text
data/index/slides.json
```

with valid page text and blocks.

## Agent 1 must NOT edit

```text
app/retrieval/**
app/qa/**
app/api/**
```

---

# AGENT 2 — RETRIEVAL ENGINE

## Ownership

Agent 2 exclusively owns:

```text
app/retrieval/**
data/index/embeddings.npy
data/index/retrieval_meta.json
```

## Tasks

Implement:

1. Slide loading from:

```text
data/index/slides.json
```

2. BM25 retrieval using:

```text
rank_bm25
```

3. Dense embedding using:

```text
intfloat/multilingual-e5-small
```

4. CPU inference.
5. Embedding cache:

```text
data/index/embeddings.npy
```

6. Reciprocal Rank Fusion.
7. Retrieval service:

```python
retrieve(question: str, top_k: int = 5)
```

8. Evidence-block ranking inside retrieved slides.

Expected return:

```python
{
    "slides": [...],
    "evidence": [...]
}
```

## Fallback

If model download/loading fails:

- allow `DENSE_ENABLED=false`
- BM25 must still work

## Definition of done

A Python call:

```python
retrieve("Gradient descent là gì?")
```

returns relevant slides and evidence.

## Agent 2 must NOT edit

```text
app/ingestion/**
app/qa/**
app/api/**
```

---

# AGENT 3 — GROUNDED QA & CITATIONS

## Ownership

Agent 3 exclusively owns:

```text
app/qa/**
```

## Tasks

1. Implement grounded prompt.
2. Accept question + evidence.
3. Assign evidence IDs:

```text
E1, E2, E3...
```

4. Call configured LLM API.
5. Ensure model only receives retrieved evidence.
6. Parse citation IDs from output.
7. Remove invalid/unrecognized citation IDs.
8. Return:

```python
{
    "answer": "...",
    "citations": [...]
}
```

9. If no LLM API key exists:
   - provide extractive fallback
   - return top evidence passages

## Required environment variables

Support at least:

```text
OPENAI_API_KEY=
LLM_MODEL=
```

Implementation may support another provider if already available.

## Definition of done

Given:

```python
question
evidence[]
```

the module produces a grounded answer with valid citation metadata.

## Agent 3 must NOT edit

```text
app/ingestion/**
app/retrieval/**
app/api/**
```

---

# AGENT 4 — API, UI, INTEGRATION & DEMO

## Ownership

Agent 4 exclusively owns:

```text
app/api/**
app/viewer/**
README.md
.env.example
requirements.txt
scripts/run_demo.py
```

## Tasks

1. Build FastAPI application.
2. Add `/api/health`.
3. Add `/api/ask`.
4. Connect:
   - retrieval service
   - QA service
5. Build minimal demo UI.

Preferred hackathon option:

```text
FastAPI + simple HTML/JS
```

Alternative:

```text
Streamlit
```

Only choose Streamlit if it materially reduces integration time.

6. Render:
   - answer
   - citation list
   - quote
   - filename
   - page number
   - clickable source
7. Serve PDFs from `data/pdf/`.
8. If feasible, implement PDF.js page opening.
9. If feasible, highlight bbox.

## Definition of done

One command starts the demo:

```bash
python scripts/run_demo.py
```

or:

```bash
uvicorn app.api.main:app --reload
```

and the browser can ask questions and view sources.

---

# 13. Shared Files Policy

These files are shared and may cause conflicts:

```text
requirements.txt
README.md
.env.example
```

Only Agent 4 should edit them.

If Agents 1-3 need a dependency, they must NOT edit `requirements.txt`.

Instead, write dependency requests to:

```text
DEPENDENCIES_REQUESTED.md
```

using append-only format:

```text
Agent 2:
- sentence-transformers
- rank-bm25
```

Agent 4 consolidates them into `requirements.txt`.

---

# 14. Cross-Agent Interface Rules

The following public Python interfaces are frozen.

## Ingestion

```python
from app.ingestion.models import SlideRecord
```

---

## Retrieval

```python
from app.retrieval.service import RetrievalService

service = RetrievalService()
result = service.retrieve(
    question="...",
    top_k=5
)
```

Expected:

```python
{
    "slides": [...],
    "evidence": [...]
}
```

---

## QA

```python
from app.qa.service import QAService

service = QAService()

result = service.answer(
    question="...",
    evidence=[...]
)
```

Expected:

```python
{
    "answer": "...",
    "citations": [...]
}
```

---

# 15. Two-Hour Timeline

## T+00 to T+10 — bootstrap

All agents:

- inspect this document
- inspect project tree
- install minimum dependencies if necessary
- create only owned directories
- do NOT change architecture

Target:

```text
project imports cleanly
```

---

## T+10 to T+45 — parallel implementation

Agent 1:
- PDF parser
- slides.json

Agent 2:
- BM25
- dense embedding
- RRF

Agent 3:
- QA prompt
- LLM call
- citation mapping

Agent 4:
- FastAPI
- UI skeleton
- routes

---

## T+45 to T+70 — integration

Agent 1:
- finalize data schema
- test real PDFs

Agent 2:
- consume real `slides.json`
- test retrieval

Agent 3:
- consume real evidence objects
- test citations

Agent 4:
- wire services together

Target by T+70:

```text
Question -> retrieval -> answer -> citation
```

must work end-to-end.

---

## T+70 to T+95 — demo hardening

Focus ONLY on visible quality:

- fix broken Vietnamese text
- improve evidence ranking
- verify citations
- make source links work
- handle missing API key
- handle empty corpus
- make error messages readable

---

## T+95 to T+110 — optional improvements

Only if MVP is stable:

Priority order:

1. bbox highlight
2. neighboring slide expansion
3. OCR fallback
4. reranker
5. visual/VLM support

Do NOT start item 4 or 5 if core flow is unstable.

---

## T+110 to T+120 — freeze

No architectural changes.

Run:

```text
fresh install
ingest
start app
ask 3-5 known questions
open citations
```

Prepare demo.

---

# 16. Integration Test Questions

Create at least five questions for which the expected page is manually known.

Example:

```json
[
  {
    "question": "Gradient descent là gì?",
    "expected_file": "lecture_x.pdf",
    "expected_page": 18
  },
  {
    "question": "Overfitting là gì?",
    "expected_file": "lecture_y.pdf",
    "expected_page": 11
  }
]
```

Do not waste time building a full evaluation framework.

For the hackathon, manually validate:

```text
Question
-> expected slide in Top 5?
-> answer grounded?
-> correct source?
```

---

# 17. Success Criteria

The demo is considered successful if:

## Critical

- PDFs can be indexed.
- Vietnamese questions work.
- Relevant slide is usually retrieved.
- Answer is generated only from evidence.
- At least one valid citation is returned.
- Clicking the citation reaches the correct PDF/page.

## Strong demo

- citation includes exact quote
- bbox exists
- evidence is highlighted
- BM25 + dense retrieval both work

## Excellent demo

- scanned slides have OCR fallback
- image-heavy slides have optional VLM description
- reranking improves results

---

# 18. Failure Strategy

Hackathon rule:

> Always preserve a working fallback.

## If dense embedding fails

Use:

```text
BM25 only
```

## If LLM API fails

Return:

```text
top retrieved evidence
```

with citations.

## If bbox highlighting fails

Open correct:

```text
PDF + page
```

## If OCR is too slow

Ignore scanned pages for MVP.

## If Vietnamese segmentation is unavailable

Use:

```text
lowercase + whitespace tokenization
```

## If integration becomes unstable

Remove:
- reranker
- OCR
- visual processing

Never remove:
- page retrieval
- evidence quote
- citation

---

# 19. Dependency Budget

Keep dependencies minimal:

```text
fastapi
uvicorn
pymupdf
numpy
sentence-transformers
rank-bm25
pydantic
python-dotenv
openai
```

Optional:

```text
faiss-cpu
paddleocr
```

Do NOT install optional packages before MVP works.

---

# 20. Environment File

`.env.example`

```text
OPENAI_API_KEY=
LLM_MODEL=gpt-5.6
DENSE_ENABLED=true
TOP_K=5
PDF_DIR=data/pdf
INDEX_DIR=data/index
```

---

# 21. Final Demo Flow

Expected operator flow:

```bash
# 1. Put PDFs here
data/pdf/

# 2. Install
pip install -r requirements.txt

# 3. Build index
python scripts/ingest.py

# 4. Start app
python scripts/run_demo.py
```

Browser:

```text
Question:
"Mạng nơ-ron tích chập là gì?"

            ↓

Answer:
"Mạng nơ-ron tích chập ... [E1]"

Sources:

[E1]
Lecture_05.pdf
Slide 17

"Mạng nơ-ron tích chập ..."

[Open evidence]
```

---

# 22. Agent Startup Prompts

Copy one prompt to each coding agent.

---

## PROMPT — AGENT 1

```text
You are Agent 1: PDF Ingestion & Data Model.

Read HACKATHON_PLAN.md completely before coding.

You are working in parallel with 3 other coding agents in the SAME project directory.

STRICT OWNERSHIP:
You may edit only:
- app/ingestion/**
- scripts/ingest.py
- data/index/slides.json
- DEPENDENCIES_REQUESTED.md (append only)

Do NOT edit retrieval, QA, API, README, requirements.txt, or files owned by other agents.

Your task:
1. Implement PDF ingestion using PyMuPDF.
2. Read all PDFs from data/pdf/.
3. Create document/page/slide records.
4. Extract native page text.
5. Extract text blocks and bbox.
6. Normalize bbox to [0,1].
7. Store page width/height if useful.
8. Produce data/index/slides.json.
9. Make scripts/ingest.py runnable.
10. Follow exactly the shared schemas and interfaces in HACKATHON_PLAN.md.

Optimize for a reliable hackathon MVP, not production architecture.

Do not add unnecessary abstractions.

When complete:
- run the ingestion script
- validate output on real PDFs
- report exactly what files you changed
- report any assumptions or blockers
```

---

## PROMPT — AGENT 2

```text
You are Agent 2: Retrieval Engine.

Read HACKATHON_PLAN.md completely before coding.

You are working in parallel with 3 other coding agents in the SAME project directory.

STRICT OWNERSHIP:
You may edit only:
- app/retrieval/**
- data/index/embeddings.npy
- data/index/retrieval_meta.json
- DEPENDENCIES_REQUESTED.md (append only)

Do NOT edit ingestion, QA, API, README, requirements.txt, or files owned by other agents.

Your task:
1. Load slide data from data/index/slides.json.
2. Implement BM25 with rank_bm25.
3. Implement dense retrieval using intfloat/multilingual-e5-small.
4. Ensure CPU-only inference works.
5. Cache slide embeddings.
6. Implement Reciprocal Rank Fusion.
7. Implement RetrievalService.retrieve(question, top_k=5).
8. Rank evidence blocks within top slides.
9. Return:
   {
     "slides": [...],
     "evidence": [...]
   }
10. If dense embedding fails, BM25-only mode must still work.

Follow the shared schemas and frozen interfaces from HACKATHON_PLAN.md exactly.

Optimize for speed and robustness.

Do not introduce external services such as Qdrant or Elasticsearch.

When complete:
- test with Vietnamese queries
- report files changed
- report dependencies needed in DEPENDENCIES_REQUESTED.md
- report blockers
```

---

## PROMPT — AGENT 3

```text
You are Agent 3: Grounded QA & Citation Engine.

Read HACKATHON_PLAN.md completely before coding.

You are working in parallel with 3 other coding agents in the SAME project directory.

STRICT OWNERSHIP:
You may edit only:
- app/qa/**
- DEPENDENCIES_REQUESTED.md (append only)

Do NOT edit ingestion, retrieval, API, README, requirements.txt, or files owned by other agents.

Your task:
1. Implement QAService.
2. Input:
   - question
   - retrieved evidence[]
3. Assign deterministic local evidence IDs E1, E2, E3...
4. Build a Vietnamese grounded-QA prompt.
5. Force the LLM to answer only from evidence.
6. Require citations [E1], [E2], ...
7. Do not allow invented citations.
8. Parse model citation IDs.
9. Drop any invalid citation IDs.
10. Return:
    {
      "answer": "...",
      "citations": [...]
    }
11. Support OPENAI_API_KEY and configurable LLM_MODEL.
12. If API access is unavailable, return an extractive fallback answer based on top evidence.

Follow the shared schemas and frozen interfaces from HACKATHON_PLAN.md exactly.

Focus on deterministic, safe grounding and clean citation mapping.

When complete:
- test with synthetic evidence
- report files changed
- report dependencies requested
- report blockers
```

---

## PROMPT — AGENT 4

```text
You are Agent 4: API, UI, Integration & Demo.

Read HACKATHON_PLAN.md completely before coding.

You are working in parallel with 3 other coding agents in the SAME project directory.

STRICT OWNERSHIP:
You may edit only:
- app/api/**
- app/viewer/**
- README.md
- requirements.txt
- .env.example
- scripts/run_demo.py
- DEPENDENCIES_REQUESTED.md

Do NOT modify files owned by ingestion, retrieval, or QA agents.

Your task:
1. Build the FastAPI app.
2. Implement:
   - GET /api/health
   - POST /api/ask
3. Integrate RetrievalService and QAService using the frozen interfaces.
4. Build a minimal web UI.
5. Display:
   - answer
   - citation ID
   - PDF filename
   - page number
   - exact evidence quote
   - Open source link
6. Serve PDFs from data/pdf/.
7. Open the correct PDF/page from citations.
8. If practical, add bbox highlighting.
9. Consolidate dependencies requested by other agents into requirements.txt.
10. Write README instructions.
11. Make one-command demo startup possible.

Do NOT overengineer the frontend.

Priority:
end-to-end working demo > styling.

When complete:
- start app
- test full flow
- report files changed
- report blockers
```

---

# 23. Critical Coordination Rule

All four agents must follow:

```text
DO NOT REFACTOR OTHER AGENTS' CODE DURING THE FIRST 70 MINUTES.
```

If an interface mismatch occurs:

1. adapt inside your owned module first
2. do not rename another agent's classes/files
3. preserve frozen public interfaces
4. communicate mismatch explicitly

Shared directory concurrency is dangerous.

The fastest strategy is:

```text
strict file ownership
+
frozen interfaces
+
late integration
```

---

# 24. Final Priority Order

When making any trade-off, use this exact priority:

```text
1. Correct PDF/page citation
2. Relevant retrieval
3. Grounded answer
4. Working end-to-end demo
5. Evidence quote
6. Bounding-box highlight
7. Dense retrieval
8. OCR
9. Reranking
10. Visual/VLM retrieval
```

Do not sacrifice items 1-4 for items 6-10.

---

# 25. Final Instruction to All Agents

This is a 2-hour hackathon build.

The system is successful when a judge can:

1. place lecture PDFs into the project,
2. ingest them,
3. ask a Vietnamese question,
4. receive a useful answer,
5. click the citation,
6. verify that the cited slide actually contains the supporting knowledge.

Build that first.

Everything else is secondary.
