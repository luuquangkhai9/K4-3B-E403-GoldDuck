"""Live HTTP checks on the main corpus; configured provider calls may be paid.

Run after starting the demo: python scripts/verify_agent.py
Reports go to ignored data/verification; credentials are never read or printed.
"""

import argparse
import json
from pathlib import Path
import sys
import time
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx

from app.ingestion.metadata import enrich_slide_metadata
from app.retrieval.blocks import merge_continuations
from app.retrieval.config import visual_evidence_text

QUESTION = "tạo mindmap các file tài liệu tôi cần học tên gì nằm ở day nào để tôi hiểu về tranformers"


def verify_sources(result, records, client):
    sources = [*result.get("citations", []),
               *(source for document in result.get("documents", []) for source in document["sources"]),
               *(node for branch in result.get("branches", []) for node in branch.get("nodes", []))]
    for source in sources:
        raw = records[source["slide_id"]]
        for key in ("filename", "document_id", "page_number", "day_id"):
            assert source[key] == raw[key], (key, source["slide_id"])
        if source.get("quote"):
            texts = ([visual_evidence_text(raw)] if source.get("evidence_type") == "visual" else
                     [raw.get("text", ""), *(block.get("text", "") for block in raw.get("blocks", [])),
                      *(block["text"] for block in merge_continuations(raw.get("blocks", []), raw.get("text", "")))])
            assert any(source["quote"] in text for text in texts), source["slide_id"]
        parameters = parse_qs(urlsplit(source["viewer_url"]).query)
        assert parameters["file"] == [source["filename"]]
        assert parameters["page"] == [str(source["page_number"])]
        if source.get("evidence_id"):
            assert parameters["evidence"] == [source["evidence_id"]]
    for document in result.get("documents", []):
        assert document["sources"]
        assert all(source["document_id"] == document["document_id"] for source in document["sources"])
        source = document["sources"][0]
        assert client.get(source["viewer_url"]).status_code == 200
        image = client.get("/api/page", params={"file": source["filename"], "page": source["page_number"]})
        assert image.status_code == 200 and image.content.startswith(b"\x89PNG")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--index", type=Path, default=ROOT / "data/index/slides.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/verification/agent_live_report.json")
    args = parser.parse_args()
    raw = json.loads(args.index.read_text(encoding="utf-8-sig"))
    records = {item["slide_id"]: enrich_slide_metadata(item) for item in (raw.get("slides", []) if isinstance(raw, dict) else raw)}
    report = {"passed": False, "cases": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=65) as client:
        def call(name, question, **extra):
            started = time.monotonic()
            response = client.post("/api/chat", json={"question": question, **extra})
            result = response.json()
            report["cases"].append({"name": name, "http_status": response.status_code,
                                    "seconds": round(time.monotonic() - started, 3), "result": result})
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            assert response.status_code == 200, (name, response.status_code)
            verify_sources(result, records, client)
            print(json.dumps({"case": name, "status": result["status"], "task": result["task"],
                              "documents": len(result["documents"]), "seconds": report["cases"][-1]["seconds"]}), flush=True)
            return result

        result = call("compound_typo_mindmap", QUESTION)
        assert result["task"] == "study_materials" and result["output_format"] == "mindmap"
        assert result["status"] == "completed", result["status"]
        assert result["grounding"]["document_review_completed"]
        assert result["debug"]["agent"]["original_question"] == QUESTION
        assert result["debug"]["agent"]["query_corrections"] == {"tranformers": "transformers"}
        assert any(document["role"] == "core" and document["day_id"] == "Day01" for document in result["documents"])
        assert result["branches"]

        followup = call("followup_documents", "tạo mindmap các tài liệu đó", context=result["context"])
        assert followup["task"] == "study_materials" and followup["documents"]
        assert set(followup["context"]["document_ids"]) <= set(result["context"]["document_ids"])

        scoped = call("scoped_text_documents", "Tôi muốn học về Transformers trong khóa học, tài liệu nào ở ngày nào?", scope=["Day01"])
        assert scoped["task"] == "study_materials" and scoped["output_format"] == "text"
        assert scoped["documents"] and all(source["day_id"] == "Day01" for source in scoped["citations"])

        qa = call("normal_qa", "Temperature là gì?", scope=["Day01"])
        assert qa["task"] == "answer" and qa["citations"]

        overview = call("day_range", "tạo mindmap từ day 1 đến day 3")
        assert overview["task"] == "day_summary"
        assert [branch["label"] for branch in overview["branches"]] == ["Day 01", "Day 02", "Day 03"]

        unknown = call("unknown_topic", "tạo mindmap các tài liệu tôi cần học về QwertyzxcUnicorn731")
        assert unknown["status"] == "no_evidence" and not unknown["documents"] and not unknown["branches"]

        for name, question, scope, expected in (
            ("unknown_day", QUESTION + " day 99", None, 404),
            ("outside_scope", QUESTION + " day 7", ["Day01"], 422),
            ("descending_range", "mindmap từ day 3 đến day 1", None, 422),
        ):
            response = client.post("/api/chat", json={"question": question, "scope": scope})
            assert response.status_code == expected, (name, response.status_code)
            report["cases"].append({"name": name, "http_status": response.status_code})
        report["passed"] = True
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": True, "cases": len(report["cases"]), "report": str(args.output)}), flush=True)


if __name__ == "__main__":
    main()
