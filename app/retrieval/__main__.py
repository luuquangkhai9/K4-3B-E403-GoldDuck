"""Build/verify dense embeddings: python -m app.retrieval --require-dense."""

import argparse
import logging
import time

from dotenv import load_dotenv

from .service import PROJECT_ROOT, RetrievalService


def main():
    load_dotenv(PROJECT_ROOT / ".env")
    parser = argparse.ArgumentParser(description="Build and check the slide retrieval index")
    parser.add_argument("--query", default="MCP và A2A khác nhau như thế nào?")
    parser.add_argument("--require-dense", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    service = RetrievalService(dense_enabled=True)
    print("Loading E5 on CPU and building/reusing embeddings...", flush=True)
    start = time.perf_counter()
    result = service.retrieve(args.query)
    dense_ready = service.dense is not None and not service.dense.failed and service.dense.embeddings is not None
    print(f"Slides: {len(service.slides)}; dense ready: {dense_ready}; elapsed: {time.perf_counter() - start:.1f}s", flush=True)
    for hit in result["slides"]:
        print(f"{hit['rank']}. {hit['filename']} - page {hit['page_number']}", flush=True)
    if args.require_dense and not dense_ready:
        raise SystemExit("Dense retrieval is not ready; see the warning above.")


if __name__ == "__main__":
    main()
