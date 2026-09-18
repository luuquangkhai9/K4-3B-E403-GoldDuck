"""Check HTTP/source contracts; semantic quality requires separate human review."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import httpx
from app.paths import load_environment
from app.ingestion.metadata import enrich_slide_metadata
from scripts.verify_agent import verify_sources


def main():
    data_root = load_environment(ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--cases", type=Path, default=ROOT.parent / "eval/golden_set.json")
    parser.add_argument("--output", type=Path, default=ROOT.parent / "eval/http_results.json")
    args = parser.parse_args()
    raw = json.loads((data_root / "data/index/slides.json").read_text(encoding="utf-8-sig"))
    records = {item["slide_id"]: enrich_slide_metadata(item) for item in (raw.get("slides", []) if isinstance(raw, dict) else raw)}
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    report = {"kind": "HTTP and source contracts; not semantic accuracy", "quality_bar_achieved": None, "cases": []}
    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=65) as client:
        for case in cases:
            started = time.monotonic()
            row = {"id": case["id"], "contract_passed": False,
                   "semantic_review": "pending" if case.get("semantic_review") else "not_applicable"}
            try:
                response = client.request(case["method"], case["path"], **{"json" if case["method"] == "POST" else "params": case["payload"]})
                row["http_status"] = response.status_code
                assert response.status_code == case["http"], "HTTP status"
                if response.status_code == 200:
                    result = response.json()
                    row["status"] = result["status"]
                    for key in ("task", "status"):
                        if key in case:
                            assert result[key] == case[key], key
                    for key in ("documents", "branches"):
                        if case.get(key):
                            assert result[key], key
                    if case.get("sources"):
                        assert result["citations"], "sources"
                    if case.get("days"):
                        assert [branch["label"] for branch in result["branches"]] == case["days"], "day branches"
                    options = (result.get("clarification") or {}).get("options", result.get("suggestions", []))
                    checked = dict(result)
                    checked["citations"] = result.get("citations", []) + [source for option in options for source in option["sources"]]
                    verify_sources(checked, records, client)
                    scope = case["payload"].get("scope")
                    if scope:
                        assert all(source["day_id"] in scope for source in checked["citations"]), "scope"
                    if result["status"] in ("abstained", "no_evidence"):
                        assert not result["citations"], "abstention sources"
                    if result["status"] == "partial" and case.get("semantic_review"):
                        row["semantic_review"] = "blocked: provider review unavailable"
                row["contract_passed"] = True
            except Exception as exc:
                row["error_type"] = type(exc).__name__
                if isinstance(exc, AssertionError):
                    row["failed_check"] = str(exc)
            row["seconds"] = round(time.monotonic() - started, 3)
            report["cases"].append(row)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(row), flush=True)
    report["contracts_passed"] = sum(case["contract_passed"] for case in report["cases"])
    report["total"] = len(cases)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["contracts_passed"] == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
