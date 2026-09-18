"""Manual corpus/API check: python -m app.qa.check_system."""

import json
import sys

import pymupdf
from fastapi.testclient import TestClient

from app.api.main import app, find_pdf, get_services
from app.qa.generator import AnswerGenerator


class ObservedGenerator(AnswerGenerator):
    def generate(self, prompt):
        self.api_success = False
        try:
            text = super().generate(prompt)
            self.api_success = bool(text)
            return text
        except Exception as exc:
            self.error_type = type(exc).__name__
            raise


def main():
    retrieval, qa = get_services()
    generator = ObservedGenerator()
    qa.generator = generator
    question = sys.argv[1] if len(sys.argv) > 1 else "Tranformer là gì"
    with TestClient(app) as client:
        response = client.post("/api/ask", json={"question": question})
        result = response.json()
        checks = []
        for citation in result.get("citations", []):
            with pymupdf.open(find_pdf(citation["filename"])) as pdf:
                page_text = pdf[citation["page_number"] - 1].get_text()
            checks.append({
                "evidence_id": citation["evidence_id"],
                "quote_on_page": " ".join(citation["quote"].split()) in " ".join(page_text.split()),
                "viewer_status": client.get(citation["viewer_url"]).status_code,
            })
        print(json.dumps({
            "question": question,
            "http_status": response.status_code,
            "llm_api_success": getattr(generator, "api_success", False),
            "api_error_type": getattr(generator, "error_type", None),
            "dense_active": retrieval.dense is not None and not retrieval.dense.failed,
            "result": result,
            "source_checks": checks,
        }, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
