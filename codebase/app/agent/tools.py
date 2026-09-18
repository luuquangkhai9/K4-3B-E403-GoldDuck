"""Application-owned tools and request-local source IDs."""

from copy import deepcopy

from app.qa.service import prepare_evidence
from app.viewer.evidence import viewer_url


class EvidenceStore:
    def __init__(self, catalog, scope=None):
        self.catalog = catalog
        self.scope = scope
        self.sources = {}
        self._keys = {}

    def add(self, evidence):
        added = []
        for item in prepare_evidence(evidence):
            metadata = self.catalog.get(item.get("document_id"))
            if not metadata or item["filename"] != metadata["filename"]:
                continue
            if item["page_number"] > metadata["total_pages"]:
                continue
            if self.scope is not None and metadata["day_id"] not in self.scope:
                continue
            if item["day_id"] != metadata["day_id"]:
                continue
            key = (item["document_id"], item["slide_id"], item["block_id"],
                   item["page_number"], item["evidence_type"], item["quote"])
            evidence_id = self._keys.get(key)
            if evidence_id is None:
                evidence_id = f"E{len(self.sources) + 1}"
                item["evidence_id"] = evidence_id
                # Never forward a provider-authored source URL.
                item["viewer_url"] = viewer_url(item)
                self.sources[evidence_id] = item
                self._keys[key] = evidence_id
            added.append(evidence_id)
        return added


class LectureTools:
    def __init__(self, retrieval, *, scope=None):
        self.retrieval = retrieval
        self.scope = scope
        catalog = retrieval.list_days()
        documents = [document for day in catalog["days"] for document in day["documents"]]
        documents += catalog.get("unassigned_documents", [])
        self.catalog = {item["document_id"]: item for item in documents
                        if scope is None or item["day_id"] in scope}
        self.store = EvidenceStore(self.catalog, scope)

    def get_document_metadata(self, document_ids):
        return [deepcopy(self.catalog[key]) for key in document_ids if key in self.catalog]

    def search_documents(self, query, *, limit=8, document_ids=None):
        result = self.retrieval.search_documents(query, scope=self.scope, limit=limit)
        allowed = set(document_ids) if document_ids is not None else set(self.catalog)
        ids = list(dict.fromkeys(
            item["document_id"] for item in result.get("slides", [])
            if item.get("document_id") in self.catalog and item["document_id"] in allowed
        ))[:limit]
        # Context references name real, scoped documents. Read those even when
        # they are absent from a fresh global top-k, rather than substitute files.
        if document_ids is not None:
            ids = [key for key in document_ids if key in self.catalog][:limit]
        self.store.add([item for item in result.get("evidence", []) if item.get("document_id") in ids])
        return {"document_ids": ids, "debug": result.get("debug", {})}

    def read_evidence(self, document_ids, query):
        ids = [key for key in document_ids if key in self.catalog][:12]
        evidence = self.retrieval.read_document_evidence(ids, query, scope=self.scope)
        self.store.add(evidence)
        return list(self.store.sources.values())

    def validate_result(self, selection, *, reviewed=True):
        verified = []
        seen = set()
        rejected = 0
        for item in selection:
            if item.role == "mention":
                continue
            metadata = self.catalog.get(item.document_id)
            ids = list(dict.fromkeys(item.evidence_ids))
            sources = [self.store.sources.get(key) for key in ids]
            if (not metadata or item.document_id in seen or not sources or
                any(source is None or source["document_id"] != item.document_id for source in sources)):
                rejected += 1
                continue
            seen.add(item.document_id)
            verified.append({**deepcopy(metadata), "reason": item.reason,
                             "role": item.role if reviewed else "candidate", "sources": deepcopy(sources),
                             "pages": sorted({source["page_number"] for source in sources})})
        return verified, rejected


def render_mindmap(documents):
    """Day -> exact filename, with every node backed by validated sources."""
    grouped = {}
    for document in documents:
        label = document.get("day_label") or "Chưa xác định ngày học"
        source = document["sources"][0]
        node = {**deepcopy(source), "label": document["filename"],
                "reason": document["reason"], "role": document["role"],
                "pages": document["pages"], "sources": deepcopy(document["sources"])}
        grouped.setdefault(label, {"label": label, "nodes": []})["nodes"].append(node)
    return sorted(grouped.values(), key=lambda branch: branch["nodes"][0].get("day_number") or 10000)
