"""One bounded coordinating agent; retrieval and source metadata stay in code."""

import json
import logging
import re
import time

from app.ingestion.metadata import normalize_scope
from app.qa.intent import extract_explicit_day_scope, extract_mindmap_topic
from app.retrieval.bm25 import tokenize
from app.retrieval.config import integer
from app.retrieval.query import extract_study_topic, is_document_discovery
from app.runtime import configured_timeout, remaining_timeout

from .contracts import DocumentSelection, StudyReview, TaskPlan
from .prompts import PLAN_INSTRUCTIONS, REVIEW_INSTRUCTIONS
from .tools import LectureTools, render_mindmap

log = logging.getLogger(__name__)
_MINDMAP = re.compile(r"mindmap|sơ đồ tư duy|so do tu duy", re.I)
_REFERENCE = re.compile(r"(?:tài liệu|chủ đề)\s+(?:đó|này)|ở trên", re.I)


class ChatAgent:
    def __init__(self, retrieval, qa):
        self.retrieval = retrieval
        self.qa = qa
        self.generator = qa.generator

    def _structured(self, data, *, instructions, contract, name, timeout):
        prompt = json.dumps(data, ensure_ascii=False)
        if hasattr(self.generator, "generate_json"):
            result = self.generator.generate_json(
                prompt, instructions=instructions, schema=contract.model_json_schema(),
                name=name, timeout=timeout,
            )
        else:
            # Preserve adapters implementing the original generate contract.
            text = self.generator.generate(prompt, instructions=instructions +
                                           "\nSCHEMA:\n" + json.dumps(contract.model_json_schema()))
            result = json.loads(re.sub(r"^```\w*\s*|\s*```$", "", text.strip()))
        return contract.model_validate(result)

    def plan(self, question, context=None, clarification_topic=None):
        explicit = extract_explicit_day_scope(question)
        mindmap = bool(_MINDMAP.search(question))
        discovery = is_document_discovery(question)
        topic = extract_study_topic(question) if discovery else extract_mindmap_topic(question) if mindmap else None
        referenced = bool(context and _REFERENCE.search(question) and
                          (not topic or (mindmap and re.search(r"chủ đề\s+(?:đó|này)", question, re.I))))
        if referenced:
            topic = context.get("topic")
            discovery = context.get("task") == "study_materials"
        if clarification_topic:
            topic = clarification_topic
        task = "study_materials" if discovery else "topic_map" if mindmap and topic else "day_summary" if mindmap else "answer"
        fallback = TaskPlan(task=task, output_format="mindmap" if mindmap else "text", topic=topic, scope=explicit)
        # Common document requests and pure day overviews need no extra model
        # roundtrip. Ambiguous mindmap/topic phrasing uses semantic planning.
        if (not self.generator.available or referenced or clarification_topic or (discovery and topic) or
            (mindmap and not discovery and topic and len(tokenize(topic)) <= 6) or
            (mindmap and explicit and not topic) or (not mindmap and not discovery)):
            return fallback, False
        try:
            plan = self._structured(
                {"MESSAGE": question, "CONTEXT": context,
                 "AVAILABLE_DAYS": self.retrieval.available_scopes},
                instructions=PLAN_INSTRUCTIONS, contract=TaskPlan, name="lecture_task_plan",
                timeout=configured_timeout("AGENT_PLANNER_TIMEOUT_SECONDS", 8),
            )
            # A planner cannot replace the requested format or forget explicit
            # days, including unavailable days that the API must reject.
            plan.output_format = fallback.output_format
            plan.scope = explicit or normalize_scope(plan.scope)
            if plan.topic and plan.topic.casefold() not in question.casefold():
                if not context or plan.topic != context.get("topic"):
                    plan.topic = fallback.topic
            if discovery:
                plan.task = "study_materials"
            if mindmap and plan.task == "answer":
                plan.task = "topic_map" if plan.topic else "day_summary"
            return plan, False
        except Exception as exc:
            log.warning("Task planning unavailable (%s); using local plan", type(exc).__name__)
            return fallback, True

    def run(self, question, *, scope=None, context=None, clarification_topic=None,
            validate_scope=None, answer_handler=None):
        started = time.monotonic()
        explicit = extract_explicit_day_scope(question)
        if explicit:
            if validate_scope:
                validate_scope(explicit)
            if scope is not None and any(day not in scope for day in explicit):
                raise ValueError("Ngày yêu cầu không nằm trong phạm vi đã chọn. Hãy điều chỉnh phạm vi học tập.")
        plan, planner_fallback = self.plan(question, context, clarification_topic)
        if plan.scope and plan.scope != explicit:
            if validate_scope:
                validate_scope(plan.scope)
            if scope is not None and any(day not in scope for day in plan.scope):
                raise ValueError("Ngày yêu cầu không nằm trong phạm vi đã chọn. Hãy điều chỉnh phạm vi học tập.")
        effective_scope = plan.scope or scope
        normalized = self.retrieval.normalize_topic(plan.topic) if plan.topic else {
            "topic": None, "aliases": [], "corrections": {},
        }
        trace = {"task": plan.task, "original_question": question,
                 "topic_original": plan.topic, "topic": normalized["topic"],
                 "query_corrections": normalized["corrections"], "scope_filter": effective_scope,
                 "planner_fallback": planner_fallback, "retrieval_rounds": 0}
        base = {"task": plan.task, "output_format": plan.output_format, "status": "completed",
                "title": normalized["topic"] or "Tổng quan ngày học", "branches": [],
                "documents": [], "citations": [], "debug": {"agent": trace}}
        topic = normalized["topic"]
        search_query = " ".join([topic or "", *normalized["aliases"]]).strip()
        if plan.task == "study_materials":
            if not topic:
                base.update(status="needs_clarification", answer="Bạn muốn tìm tài liệu học về chủ đề nào?")
            else:
                reference_ids = (context or {}).get("document_ids") if _REFERENCE.search(question) else None
                base = self._study(question, topic, search_query, effective_scope, base, reference_ids)
        elif plan.task == "day_summary":
            if not effective_scope:
                base.update(status="needs_clarification", answer="Bạn muốn xem mindmap về chủ đề hoặc ngày học nào?")
            else:
                days = [(day, self.retrieval.mindmap_nodes(day)) for day in effective_scope]
                result = self.qa.overview_mindmap(days)
                base.update(result, answer="Sơ đồ tổng quan các ngày học đã chọn.")
                if not base["branches"]:
                    base.update(status="no_evidence", answer="Chưa có nội dung phù hợp để tạo sơ đồ cho các ngày này.")
        elif plan.task == "topic_map":
            if not topic:
                base.update(status="needs_clarification", answer="Bạn muốn tạo mindmap về chủ đề nào?")
            elif self.retrieval.topic_supported(topic, scope=effective_scope) is False:
                base.update(status="no_evidence", answer=f"Chưa tìm thấy nguồn phù hợp về {topic} trong phạm vi đã chọn.")
            else:
                retrieved = self.retrieval.retrieve(search_query, top_k=5, scope=effective_scope)
                result = self.qa.mindmap(topic=topic, evidence=retrieved.get("evidence", []))
                base.update(result, answer=f"Sơ đồ kiến thức về {topic}, kèm nguồn bài giảng.")
                trace["retrieval_rounds"] = 1
                if not base["branches"]:
                    base.update(status="no_evidence", answer=f"Chưa tìm được đủ nội dung phù hợp về {topic} để tạo mindmap.")
        else:
            resolved_question = question + "\nChủ đề người dùng làm rõ: " + clarification_topic if clarification_topic else question
            if answer_handler:
                result = answer_handler(resolved_question, effective_scope)
            else:
                retrieved = self.retrieval.retrieve(resolved_question, scope=effective_scope)
                result = self.qa.answer(question=resolved_question, evidence=retrieved.get("evidence", []))
            if hasattr(result, "model_dump"):
                result = result.model_dump()
            base.update({key: value for key, value in result.items() if key not in {"debug", "status"}})
            base["status"] = {"answered": "completed", "abstained": "no_evidence", "error": "model_unavailable"}.get(result.get("status"), result.get("status", "completed"))
            base["debug"].update(result.get("debug") or {})
            if (result.get("grounding") or {}).get("no_answer"):
                base["status"] = "no_evidence"
        if normalized["corrections"]:
            notice = "; ".join(f"{original} → {corrected}" for original, corrected in normalized["corrections"].items())
            base["answer"] = f"Đã chuẩn hóa chủ đề: {notice}.\n\n" + base["answer"]
        trace["elapsed_seconds"] = round(time.monotonic() - started, 3)
        base["context"] = {"task": plan.task, "topic": topic,
                           "document_ids": [document["document_id"] for document in base["documents"]]}
        return base

    def _review(self, tools, question, topic, *, last_round):
        # Read pages already include nearby text. Avoid repeatedly sending a
        # page plus its overlapping blocks, viewer URLs and layout metadata.
        pages = {}
        for source in tools.store.sources.values():
            key = (source["slide_id"], source["evidence_type"])
            if key not in pages or len(source["quote"]) > len(pages[key]["quote"]):
                pages[key] = source
        evidence = [{key: source[key] for key in
                     ("evidence_id", "document_id", "page_number", "evidence_type", "quote")}
                    for source in pages.values()]
        for source in evidence:
            source["quote"] = source["quote"][:1600]
        catalog = [{key: document[key] for key in ("document_id", "filename", "title")}
                   for document in tools.get_document_metadata(list(dict.fromkeys(
                       source["document_id"] for source in evidence)))]
        return self._structured(
            {"QUESTION": question, "TOPIC": topic, "LAST_ROUND": last_round,
             "CATALOG": catalog, "EVIDENCE": evidence},
            instructions=REVIEW_INSTRUCTIONS, contract=StudyReview, name="lecture_study_review",
            timeout=configured_timeout("AGENT_REVIEW_TIMEOUT_SECONDS", 20),
        )

    @staticmethod
    def _direct_matches(tools, topic):
        """Unavailable models expose exact mentions, not guessed study advice."""
        terms = set(tokenize(topic))
        grouped = {}
        for key, source in tools.store.sources.items():
            tokens = set(tokenize(source["quote"]))
            expanded = tokens | ({"transformers"} if "transformer" in tokens else set()) | ({"transformer"} if "transformers" in tokens else set())
            if terms and terms <= expanded:
                grouped.setdefault(source["document_id"], []).append(key)
        return [DocumentSelection(document_id=key, evidence_ids=ids[:3], role="supporting",
                                  reason="Có đoạn nhắc trực tiếp chủ đề; chưa thẩm định mức độ phù hợp để học.")
                for key, ids in grouped.items()]

    def _study(self, question, topic, query, scope, base, reference_ids):
        trace = base["debug"]["agent"]
        tools = LectureTools(self.retrieval, scope=scope)
        if self.retrieval.topic_supported(topic, scope=scope) is False:
            base.update(status="no_evidence", answer=f"Chưa tìm thấy nguồn phù hợp về {topic} trong phạm vi đã chọn.")
            trace["offline_absence_check"] = True
            return base
        limit = min(12, integer("AGENT_MAX_DOCUMENTS", 8))
        documents = []
        status = "completed"
        trace["queries"] = []
        trace["invalid_selections_removed"] = 0
        for round_number in range(1 if reference_ids is not None else 2):
            trace["retrieval_rounds"] += 1
            trace["queries"].append(query)
            try:
                found = tools.search_documents(query, limit=limit, document_ids=reference_ids)
                trace["retrieval"] = found["debug"]
                tools.read_evidence(found["document_ids"], query)
            except TimeoutError:
                status = "partial" if documents else "retrieval_timeout"
                break
            if not tools.store.sources:
                status = "no_evidence"
                break
            if not self.generator.available:
                documents, rejected = tools.validate_result(self._direct_matches(tools, topic), reviewed=False)
                status = "partial" if documents else "model_unavailable"
                trace["review_fallback"] = True
                break
            try:
                review = self._review(tools, question, topic, last_round=bool(round_number) or reference_ids is not None)
                selected, rejected = tools.validate_result(review.documents)
                trace["invalid_selections_removed"] += rejected
                if rejected and not selected:
                    raise ValueError("No valid selected sources")
                documents = selected[:limit]
                if rejected:
                    status = "partial"
            except Exception as exc:
                log.warning("Document review unavailable (%s)", type(exc).__name__)
                trace["review_fallback"] = True
                trace["review_failure"] = type(exc).__name__
                if not documents:
                    documents, _ = tools.validate_result(self._direct_matches(tools, topic), reviewed=False)
                status = "partial" if documents else "invalid_output" if isinstance(exc, ValueError) else "model_unavailable"
                break
            if round_number or reference_ids is not None or not review.missing_queries:
                break
            query = review.missing_queries[0].strip()[:200]
            try:
                enough_time = remaining_timeout(45) > 8
            except TimeoutError:
                enough_time = False
            if not query or query in trace["queries"] or not enough_time:
                if documents:
                    status = "partial"
                break
        trace["source_count"] = len(tools.store.sources)
        if not documents:
            if status == "completed":
                status = "no_evidence"
            messages = {
                "no_evidence": f"Chưa tìm được tài liệu có nội dung đủ phù hợp về {topic} trong phạm vi đã chọn.",
                "retrieval_timeout": "Tìm tài liệu quá thời gian xử lý. Vui lòng thử lại; chưa thể kết luận kho thiếu nội dung.",
                "model_unavailable": "Model chưa sẵn sàng để thẩm định tài liệu; chưa thể kết luận kho thiếu nội dung.",
                "invalid_output": "Chưa thẩm định được tài liệu do kết quả model không hợp lệ. Vui lòng thử lại.",
            }
            base.update(status=status, answer=messages.get(status, messages["invalid_output"]))
            return base
        citations = list({source["evidence_id"]: source for document in documents
                          for source in document["sources"]}.values())
        text = f"Các tài liệu liên quan đến {topic} tìm được trong phạm vi đã chọn:\n\n"
        text += "\n\n".join(
            f"{document['filename']} — {document.get('day_label') or 'chưa xác định ngày học'}, "
            f"slide {', '.join(map(str, document['pages']))}: "
            f"{'[Bổ trợ] ' if document['role'] == 'supporting' else '[Chưa thẩm định] ' if document['role'] == 'candidate' else ''}{document['reason']} "
            + " ".join(f"[{source['evidence_id']}]" for source in document["sources"])
            for document in documents
        )
        text += "\n\nDanh sách dựa trên các nguồn tìm được, chưa khẳng định bao phủ toàn bộ khóa học."
        if status == "partial":
            text += " Một phần xử lý chưa hoàn tất; xem nguồn để kiểm tra nội dung."
        base.update(status=status, title=f"Tài liệu học về {topic}", answer=text, documents=documents,
                    citations=citations, grounding={"status": "grounded", "no_answer": False,
                    "used_evidence_ids": [source["evidence_id"] for source in citations],
                    "document_review_completed": not trace.get("review_fallback", False)})
        if base["output_format"] == "mindmap":
            base["branches"] = render_mindmap(documents)
        return base
