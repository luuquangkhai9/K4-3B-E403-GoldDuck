"""Offline clarification and source-backed abstention, without fixed topics."""

import re

from app.retrieval.bm25 import tokenize
from app.retrieval.query import extract_study_topic
from .prompts import INSUFFICIENT_EVIDENCE

_DEICTIC = re.compile(r"\b(?:cái này|cái đó|điều đó|thứ đó|nó|chủ đề này|chủ đề đó)\b", re.I)
_FILLER = set("cái nó chạy hoạt động giải thích giúp tôi mình học kiến thức chủ đề tạo tao vẽ mindmap sơ đồ tư duy đúng nghĩa tóm tắt thế cách dùng làm việc thêm số buổi ngày day file tài liệu bài giảng ở trên hiểu muốn này đó biết cho xem hãy lại nữa bạn".split())
_MAP = re.compile(r"mindmap|sơ đồ tư duy|so do tu duy", re.I)


def question_topic(question):
    topic = extract_study_topic(question)
    if topic:
        return topic
    match = re.fullmatch(r"\s*(.+?)\s+(?:là gì|nghĩa là gì|là như thế nào)\s*[?.!]*", question, re.I)
    if not match:
        match = re.fullmatch(r"\s*what is\s+(.+?)\s*[?.!]*", question, re.I)
    if match:
        return match[1].strip()
    words = tokenize(question)
    return words[0] if len(words) == 1 and words[0] not in _FILLER else None


class QueryPolicy:
    def __init__(self, retrieval):
        self.retrieval = retrieval

    def clarification(self, question, *, scope=None, context=None, selected_topic=None):
        if selected_topic:
            return None
        if context and context.get("topic") and re.search(r"(?:tài liệu|chủ đề)\s+(?:đó|này)", question, re.I):
            return None
        terms = set(tokenize(question))
        meaningful = set(self.retrieval.subject_terms(question, scope=scope)) - _FILLER
        vague = question.strip(' .?!').casefold() in {"là gì", "nghĩa là gì", "giải thích", "giải thích thêm", "giúp tôi"}
        ambiguous = not meaningful and (vague or bool(_DEICTIC.search(question)) or (bool(terms) and terms <= _FILLER))
        # A selected Day is enough to interpret a pure mindmap overview.
        if _MAP.search(question) and scope and not _DEICTIC.search(question):
            ambiguous = False
        if not ambiguous:
            return None
        query = (context or {}).get("topic") or question
        options = self.retrieval.concept_suggestions(query, scope=scope)
        return {"original_query": question, "question": "Bạn muốn hỏi về chủ đề nào? Chọn một chủ đề có nguồn hoặc nhập chủ đề khác.",
                "scope": scope, "options": options}

    def abstention(self, question, *, scope=None):
        return {"answer": INSUFFICIENT_EVIDENCE,
                "status": "abstained", "citations": [],
                "suggestions": self.retrieval.concept_suggestions(question, scope=scope),
                "grounding": {"status": "insufficient_evidence", "no_answer": True,
                              "used_evidence_ids": [], "suggestions_are_answers": False}}

    @staticmethod
    def direct_topic_match(topic, evidence):
        terms = set(tokenize(topic))
        for source in evidence:
            tokens = set(tokenize(source.get("quote", source.get("text", ""))))
            if "transformer" in tokens or "transformers" in tokens:
                tokens.update(("transformer", "transformers"))
            if terms and terms <= tokens:
                return True
        return False
