"""Extract study topics and conservatively repair typos using corpus terms."""

from difflib import SequenceMatcher, get_close_matches
import re


def is_document_discovery(question):
    return bool(re.search(
        r"(?:tài liệu|tệp|file|bài giảng|slide).*nào|(?:học|tìm).*(?:tài liệu|bài giảng|file)|"
        r"(?:mindmap|sơ đồ tư duy|so do tu duy).*(?:tài liệu|bài giảng|file|tệp)",
        question, re.I,
    ))


def extract_study_topic(question):
    """Conservative local fallback; semantic planning handles other phrasing."""
    match = re.search(
        r"(?:học|tìm hiểu|hiểu|tìm tài liệu)\s+về\s+(.+?)(?:[,;?]|$)", question, re.I,
    )
    if not match:
        match = re.search(r"(?:tài liệu|bài giảng|file|tệp).*?\s+về\s+(.+?)(?:[,;?]|$)", question, re.I)
    if not match:
        return None
    topic = re.split(
        r"\s+(?:trong khóa học|trong khoá học|tôi cần học|nằm ở|thuộc ngày|thuộc day|"
        r"ở day|vào day|từ day|từ ngày|từ buổi|day\s*\d|buổi\s*\d)", match[1], maxsplit=1, flags=re.I,
    )[0]
    topic = re.sub(r"^(?:kiến thức|chủ đề)\s+", "", topic, flags=re.I)
    return topic.strip(' .!:"“”')[:200] or None


def normalize_topic(topic, frequencies):
    """Shared typo repair; do not choose between ambiguous corpus terms."""
    vocabulary = sorted(word for word, count in frequencies.items()
                        if count >= 2 and re.fullmatch(r"[a-z]{7,}", word))
    corrections = {}

    def repair(match):
        original = match[0]
        word = original.lower()
        if word in frequencies:
            return original
        matches = get_close_matches(word, vocabulary, n=2, cutoff=0.9)
        if not matches:
            return original
        if len(matches) > 1 and (
            SequenceMatcher(None, word, matches[0]).ratio() -
            SequenceMatcher(None, word, matches[1]).ratio() < 0.03
        ):
            return original
        corrections[original] = matches[0]
        return matches[0]

    normalized = re.sub(r"(?<!\w)[A-Za-z]{7,}(?!\w)", repair, topic)
    aliases = []
    if re.search(r"\btransformers?\b", normalized, re.I):
        aliases = [word for word in ("transformer", "transformers")
                   if frequencies.get(word) and not re.search(rf"\b{word}\b", normalized, re.I)]
    return normalized, aliases, corrections


def prepare_query(question, frequencies):
    discovery = is_document_discovery(question)
    topic = extract_study_topic(question) if discovery else None
    query, aliases, corrections = normalize_topic(topic or question, frequencies)
    if aliases:
        query += " " + " ".join(aliases)
    return query, discovery, corrections
