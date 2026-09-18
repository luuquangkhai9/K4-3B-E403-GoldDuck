"""Extract study topics and conservatively repair typos using corpus terms."""

from difflib import get_close_matches
import re


def is_document_discovery(question):
    return bool(re.search(
        r"(?:tài liệu|tệp|bài giảng|slide).*nào|(?:học|tìm).*(?:tài liệu|bài giảng)",
        question, re.I,
    ))


def prepare_query(question, frequencies):
    discovery = is_document_discovery(question)
    topic = re.search(r"(?:học|tìm hiểu|tìm tài liệu)\s+về\s+(.+?)(?:[,;?.]|$)", question, re.I) if discovery else None
    query = topic[1].strip() if topic else question
    corrections = {}
    if topic:
        vocabulary = sorted(word for word, count in frequencies.items()
                            if count >= 2 and re.fullmatch(r"[a-z]{7,}", word))

        def repair(match):
            original = match[0]
            word = original.lower()
            if word in frequencies:
                return original
            matches = get_close_matches(word, vocabulary, n=1, cutoff=0.9)
            if not matches:
                return original
            corrections[original] = matches[0]
            return matches[0]

        query = re.sub(r"(?<!\w)[A-Za-z]{7,}(?!\w)", repair, query)
        # Slide titles use both the singular and plural forms of this topic.
        if re.search(r"\btransformers\b", query, re.I) and frequencies.get("transformer"):
            query += " transformer"
    return query, discovery, corrections
