"""Verify configured providers and five real V2 flows on a small PDF fixture.

Run from any directory: python scripts/verify_live.py
Provider calls can incur charges. Cache and reports stay in data/verification.
"""

import argparse
import copy
import json
import os
from pathlib import Path
import re
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from app.paths import load_environment

ROOT = load_environment(ROOT)

import pymupdf
from fastapi.testclient import TestClient

from app.api.main import app
from app.ingestion.ingest import ingest_pdfs
from app.ingestion.vision import VisionAdapter, VisionConfig, VisionEnricher
from app.qa.generator import AnswerGenerator
from app.qa.service import QAService
from app.retrieval.service import RetrievalService


def error_details(exc):
    details = {"type": type(exc).__name__}
    status = getattr(exc, "status_code", getattr(exc, "code", None))
    if isinstance(status, int):
        details["http_status"] = status
    reason = getattr(exc, "reason", None)
    errno = getattr(reason, "errno", None)
    if isinstance(errno, int):
        details["network_errno"] = errno
    # Provider messages and bodies can contain credentials; do not include them.
    return details


class ObservedVision(VisionAdapter):
    def __init__(self, config):
        super().__init__(config)
        self.calls = 0
        self.errors = []

    def analyze(self, image, native_text):
        self.calls += 1
        try:
            return super().analyze(image, native_text)
        except Exception as exc:
            self.errors.append(error_details(exc))
            raise


class ObservedGenerator(AnswerGenerator):
    def __init__(self):
        super().__init__()
        self.calls = 0
        self.successes = 0
        self.errors = []

    def generate(self, prompt):
        self.calls += 1
        try:
            result = super().generate(prompt)
            self.successes += bool(result)
            return result
        except Exception as exc:
            self.errors.append(error_details(exc))
            raise


class ObservedRetrieval(RetrievalService):
    def retrieve(self, question, top_k=5):
        result = super().retrieve(question, top_k)
        self.last_result = result
        return result


def build_fixture(path):
    if path.exists():
        return
    passages = {
        1: "Quy trình GoldDuck kiểm tra mã xác nhận màu xanh trước khi mở cổng. "
           "Mã xác nhận hợp lệ của bài kiểm thử là GD-731. Khi mã hợp lệ, cổng mở; "
           "khi mã sai, cổng giữ trạng thái đóng và người dùng phải kiểm tra lại mã.",
        2: "The amber sensor activation threshold is 42 degrees Celsius. "
           "The cobalt sensor reset threshold is 18 degrees Celsius. "
           "Each threshold belongs to its named sensor and they must not be interchanged.",
        4: "The Nimbus protocol has two sequential stages. Stage 1 verifies the blue badge. "
           "The next slide explains the required stage 2 check. Both stages must complete "
           "before access is granted by this protocol.",
        5: "Stage 2 of the Nimbus protocol checks the yellow access token. "
           "The token must be valid after the blue badge check described on the previous "
           "slide. If the yellow token is invalid, the protocol denies access.",
    }
    with pymupdf.open() as pdf:
        for number in range(1, 6):
            page = pdf.new_page(width=800, height=500)
            if number in passages:
                page.insert_htmlbox((40, 50, 760, 440), "<p>" + passages[number] + "</p>",
                                    css="p {font-family:sans-serif; font-size:22px;}")
            else:
                with pymupdf.open() as drawing:
                    diagram = drawing.new_page(width=800, height=500)
                    diagram.insert_text((190, 110), "Visual Oriole Pipeline", fontsize=26)
                    for x, label in ((40, "Input"), (300, "Convolution"), (560, "Pooling")):
                        diagram.draw_rect((x, 210, x + 190, 300), fill=(0.8, 0.9, 1))
                        diagram.insert_text((x + 12, 260), label, fontsize=22)
                    for x in (230, 490):
                        diagram.draw_line((x, 255), (x + 70, 255))
                        diagram.draw_line((x + 60, 245), (x + 70, 255))
                        diagram.draw_line((x + 60, 265), (x + 70, 255))
                    page.insert_image(page.rect, stream=diagram.get_pixmap().tobytes("png"))
        pdf.save(path)


def check_sources(client, payload, pdf_dir):
    checks = []
    ids = {citation["evidence_id"] for citation in payload.get("citations", [])}
    tokens = re.findall(r"\[E[1-9]\d*\]", payload.get("answer", ""))
    valid_ids = all(token[1:-1] in ids for token in tokens)
    for citation in payload.get("citations", []):
        filename, number = citation["filename"], citation["page_number"]
        with pymupdf.open(pdf_dir / filename) as pdf:
            native = pdf[number - 1].get_text()
        visual = citation.get("evidence_type") == "visual"
        native_quote_valid = visual or " ".join(citation["quote"].split()) in " ".join(native.split())
        image = client.get("/api/page", params={"file": filename, "page": number})
        checks.append({"page": number, "type": citation.get("evidence_type", "native"),
                       "filename": filename,
                       "role": citation.get("source_role", "primary"),
                       "quote_valid": native_quote_valid,
                       "viewer_ok": client.get(citation["viewer_url"]).status_code == 200,
                       "image_ok": image.status_code == 200 and image.content.startswith(b"\x89PNG")})
    return valid_ids, checks


def verify_corpus(only=None):
    """Exercise the existing corpus plus one image-heavy lecture slide."""
    directory = ROOT / "data" / "verification"
    directory.mkdir(parents=True, exist_ok=True)
    pdf_dir = Path(os.getenv("PDF_DIR", "data/pdf"))
    pdf_dir = pdf_dir if pdf_dir.is_absolute() else ROOT / pdf_dir
    index_dir = Path(os.getenv("INDEX_DIR", "data/index"))
    index_dir = index_dir if index_dir.is_absolute() else ROOT / index_dir
    payload = json.loads((index_dir / "slides.json").read_text(encoding="utf-8-sig"))
    slides = payload.get("slides", []) if isinstance(payload, dict) else payload
    report = {"slides": len(slides), "documents": len({slide["filename"] for slide in slides}), "checks": []}
    generator = ObservedGenerator()

    def record(name, passed, **details):
        result = {"name": name, "passed": bool(passed), **details}
        report["checks"].append(result)
        print(json.dumps(result, ensure_ascii=True), flush=True)

    previous = {name: getattr(app.state, name, None) for name in ("retrieval_service", "qa_service")}
    try:
        with TestClient(app) as client:
            app.state.retrieval_service = ObservedRetrieval(index_dir)
            app.state.qa_service = QAService(generator=generator)
            for name, question, terms in (
                ("real_corpus_native", "MCP server công bố ba loại capability nào? Giữ nguyên tên tiếng Anh.",
                 ("tools", "resources", "prompts")),
                ("real_corpus_no_answer", "Ngày sinh chính xác của nhân vật Zyxwvu-98765 là ngày nào?", ()),
            ):
                if only and name != {"vietnamese_native": "real_corpus_native", "no_answer": "real_corpus_no_answer"}.get(only):
                    continue
                print("Checking " + name + "...", flush=True)
                response = client.post("/api/ask", json={"question": question})
                result = response.json()
                valid_ids, sources = check_sources(client, result, pdf_dir)
                grounding, debug = result.get("grounding") or {}, result.get("debug") or {}
                passed = response.status_code == 200 and valid_ids and debug.get("reranker_used")
                passed = passed and debug.get("block_ranking_method") == "e5" and not grounding.get("extractive_fallback")
                if terms:
                    passed = passed and sources and all(term in result.get("answer", "").casefold() for term in terms)
                    passed = passed and all(s["quote_valid"] and s["viewer_ok"] and s["image_ok"] for s in sources)
                else:
                    passed = passed and not sources and grounding.get("no_answer")
                selected = app.state.retrieval_service.last_result
                record(name, passed, answer=result.get("answer"), sources=sources, grounding=grounding, debug=debug,
                       primary_pages=[{"file": s["filename"], "page": s["page_number"]} for s in selected.get("slides", [])],
                       selected_evidence=selected.get("evidence", []))

            # The manually inspected slide displays softmax(QK^T/sqrt(d_k))V.
            candidates = [slide for slide in slides if slide["filename"].startswith("Day01/")
                          and "Self-Attention" in slide.get("text", "") and slide["page_number"] == 23]
            if candidates and only in (None, "visual"):
                visual = copy.deepcopy(candidates[0])
                config = VisionConfig.from_env()
                adapter = ObservedVision(config)
                with pymupdf.open(pdf_dir / visual["filename"]) as pdf:
                    page = pdf[visual["page_number"] - 1]
                    enricher = VisionEnricher(config, directory / "real_vision", adapter)
                    enricher.enrich(page, visual)
                    before = adapter.calls
                    repeated = copy.deepcopy(candidates[0])
                    enricher.enrich(page, repeated)
                record("real_vision_cache", visual.get("visual_analysis", {}).get("status") == "success"
                       and repeated.get("visual_analysis", {}).get("cached") is True and adapter.calls == before,
                       errors=adapter.errors, summary=visual.get("visual_analysis", {}).get("summary"))
                sample = [copy.deepcopy(slide) for slide in slides if slide["filename"] == visual["filename"]
                          and abs(slide["page_number"] - visual["page_number"]) <= 1]
                sample = [visual if slide["slide_id"] == visual["slide_id"] else slide for slide in sample]
                sample_index = directory / "real_sample_index"
                sample_index.mkdir(exist_ok=True)
                (sample_index / "slides.json").write_text(json.dumps(sample, ensure_ascii=False), encoding="utf-8")
                app.state.retrieval_service = RetrievalService(sample_index)
                question = "Công thức Attention(Q,K,V) trên slide Scaled Dot-Product Attention trang 23 là gì?"
                response = client.post("/api/ask", json={"question": question})
                result = response.json()
                valid_ids, sources = check_sources(client, result, pdf_dir)
                grounding, debug = result.get("grounding") or {}, result.get("debug") or {}
                passed = response.status_code == 200 and valid_ids and debug.get("reranker_used")
                passed = passed and not grounding.get("extractive_fallback") and any(
                    s["page"] == 23 and s["type"] == "visual" for s in sources)
                passed = passed and "softmax" in result.get("answer", "").casefold() and all(
                    s["viewer_ok"] and s["image_ok"] and s["quote_valid"] for s in sources)
                record("real_visual_qa", passed, answer=result.get("answer"), sources=sources, grounding=grounding, debug=debug)
            elif only in (None, "visual"):
                record("real_visual_qa", False, reason="expected_sample_not_in_index")
    finally:
        for name, service in previous.items():
            if service is None:
                if hasattr(app.state, name):
                    delattr(app.state, name)
            else:
                setattr(app.state, name, service)
    report["llm_errors"] = generator.errors
    report["passed"] = all(check["passed"] for check in report["checks"])
    destination = directory / ("real_corpus_report_" + only + ".json" if only else "real_corpus_report.json")
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Report: " + str(destination), flush=True)
    return 0 if report["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=("vietnamese_native", "english_to_vietnamese", "visual", "neighbor", "no_answer"))
    parser.add_argument("--corpus", action="store_true", help="Check the real corpus and one visual lecture slide")
    args = parser.parse_args()
    if args.corpus:
        if args.only not in (None, "vietnamese_native", "no_answer", "visual"):
            parser.error("--corpus supports --only vietnamese_native, no_answer, or visual")
        return verify_corpus(args.only)
    directory = ROOT / "data" / "verification"
    pdf_dir, index_dir = directory / "pdf", directory / "index"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    build_fixture(pdf_dir / "verification.pdf")
    config = VisionConfig.from_env()
    adapter = ObservedVision(config)
    report = {"models": {"vision": config.model, "reranker": os.getenv("RERANK_MODEL"),
                         "llm": os.getenv("LLM_MODEL")}, "checks": [], "provider_errors": {}}

    def record(name, passed, **details):
        report["checks"].append({"name": name, "passed": bool(passed), **details})
        print(json.dumps(report["checks"][-1], ensure_ascii=True), flush=True)

    print("Checking ingestion and Vision (at most one uncached image slide)...", flush=True)
    ingest_pdfs(pdf_dir, index_dir / "slides.json", vision_config=config, vision_adapter=adapter)
    slides = json.loads((index_dir / "slides.json").read_text(encoding="utf-8"))
    visual = slides[2].get("visual_analysis", {})
    record("vision_api", visual.get("status") == "success", status=visual.get("status"),
           cached=visual.get("cached"), summary=visual.get("summary"))
    if visual.get("status") == "success":
        before = adapter.calls
        ingest_pdfs(pdf_dir, index_dir / "slides.json", vision_config=config, vision_adapter=adapter)
        cached = json.loads((index_dir / "slides.json").read_text(encoding="utf-8"))[2].get("visual_analysis", {})
        record("vision_cache", cached.get("cached") is True and adapter.calls == before)
    else:
        record("vision_cache", False, reason="vision_did_not_succeed", errors=adapter.errors)
    report["provider_errors"]["vision"] = adapter.errors

    generator = ObservedGenerator()
    questions = [
        ("vietnamese_native", "Mã xác nhận hợp lệ của quy trình GoldDuck là gì?", {1}),
        ("english_to_vietnamese", "Cảm biến amber kích hoạt ở nhiệt độ bao nhiêu?", {2}),
        ("visual", "Visual Oriole Pipeline gồm những bước nào?", {3}),
        ("neighbor", "Hai giai đoạn của Nimbus protocol kiểm tra những gì?", {4, 5}),
        ("no_answer", "Ngày sinh chính xác của nhân vật Zyxwvu-98765 là ngày nào?", set()),
    ]
    if args.only:
        questions = [item for item in questions if item[0] == args.only]
    environment = {"PDF_DIR": str(pdf_dir), "INDEX_DIR": str(index_dir)}
    previous = {name: getattr(app.state, name, None) for name in ("retrieval_service", "qa_service")}
    try:
        with patch.dict(os.environ, environment), TestClient(app) as client:
            retrieval = RetrievalService(index_dir=index_dir)
            app.state.retrieval_service = retrieval
            app.state.qa_service = QAService(generator=generator)
            for name, question, expected in questions:
                print("Checking " + name + "...", flush=True)
                # One primary slide forces the second Nimbus page to be supplied
                # by neighbor expansion, rather than a second primary hit.
                with patch.dict(os.environ, {"TOP_K": "1"} if name == "neighbor" else {}):
                    response = client.post("/api/ask", json={"question": question})
                payload = response.json()
                valid_ids, sources = check_sources(client, payload, pdf_dir)
                debug, grounding = payload.get("debug") or {}, payload.get("grounding") or {}
                pages = {item["page"] for item in sources}
                passed = response.status_code == 200 and valid_ids and all(
                    item["quote_valid"] and item["viewer_ok"] and item["image_ok"] for item in sources)
                passed = passed and (expected.issubset(pages) if expected else not sources and grounding.get("no_answer"))
                passed = passed and debug.get("reranker_used") and debug.get("block_ranking_method") == "e5"
                passed = passed and not grounding.get("extractive_fallback")
                if name == "visual":
                    passed = passed and any(item["type"] == "visual" for item in sources)
                if name == "neighbor":
                    passed = passed and any(item["role"] == "neighbor" for item in sources)
                record(name, passed, http_status=response.status_code, answer=payload.get("answer"),
                       sources=sources, debug=debug, grounding=grounding)
            record("dense_cpu", retrieval.dense is not None and not retrieval.dense.failed
                   and retrieval.dense.embeddings is not None)
            record("llm_api", generator.successes > 0 and not generator.errors,
                   calls=generator.calls, successes=generator.successes)
            report["provider_errors"]["llm"] = generator.errors
            # Disable optional providers and verify the original lexical/extractive path.
            with patch.dict(os.environ, {"RERANK_ENABLED": "false", "NEIGHBOR_EXPANSION_ENABLED": "false",
                                         "CITATION_VALIDATION_ENABLED": "false", "NO_ANSWER_ENABLED": "false"}):
                v1_index = directory / "v1_index"
                ingest_pdfs(pdf_dir, v1_index / "slides.json", vision_config=VisionConfig())
                app.state.retrieval_service = RetrievalService(v1_index, dense_enabled=False)
                app.state.qa_service = QAService(generator=AnswerGenerator(api_key=""))
                response = client.post("/api/ask", json={"question": questions[0][1]})
                payload = response.json()
                valid_ids, sources = check_sources(client, payload, pdf_dir)
                record("v1_compatibility", response.status_code == 200 and valid_ids and any(
                    item["page"] == 1 for item in sources) and all(item["quote_valid"] for item in sources))
    finally:
        for name, service in previous.items():
            if service is None:
                if hasattr(app.state, name):
                    delattr(app.state, name)
            else:
                setattr(app.state, name, service)
    report["passed"] = all(item["passed"] for item in report["checks"])
    destination = directory / ("live_report_" + args.only + ".json" if args.only else "live_report.json")
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Report: " + str(destination), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
