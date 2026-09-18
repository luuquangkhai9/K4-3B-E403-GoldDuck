"""Deterministic day ranges/lists for mindmap requests, including offline mode."""

import re

from app.ingestion.metadata import normalize_scope

_DAY = r"(?:day|buổi|ngày)(?:\s+học)?(?:\s+số)?"
_REFERENCE = re.compile(rf"(?<!\w){_DAY}\s*(\d{{1,4}})(?!\d)", re.I)
_RANGE = re.compile(rf"(?<!\w)(?:từ\s+)?{_DAY}\s*(\d{{1,4}})\s*(?:đến|tới|[-–—])\s*(?:{_DAY}\s*)?(\d{{1,4}})(?!\d)", re.I)
_LIST = re.compile(rf"(?<!\w){_DAY}\s*\d{{1,4}}(?:\s*(?:,|và|&)\s*(?:{_DAY}\s*)?\d{{1,4}})+(?!\d)", re.I)
_TRIGGER = re.compile(r"mindmap|sơ đồ tư duy|so do tu duy", re.I)
_FILLER = re.compile(
    r"(?<!\S)(?:tôi muốn|mình muốn|tôi cần|mình cần|làm ơn|toàn bộ|tổng hợp|tổng quan|ôn tập|"
    r"tạo|tao|vẽ|làm|xem|hãy|giúp(?: tôi| mình)?|cho tôi|cho mình|dùm|giùm|về|của|"
    r"kiến thức|nội dung|đi|nhé|nha|ạ|thử|coi|xíu|chút|nhỉ|luôn|với|cái)(?!\S)", re.I,
)


def extract_explicit_day_scope(message):
    """Parse days for any chat task, preserving unknown days for validation."""
    days = []

    def replace_range(match):
        start, end = map(int, match.groups())
        if start < 1 or end < start or end - start + 1 > 50:
            raise ValueError("Phạm vi ngày không hợp lệ; dùng ngày tăng dần, tối đa 50 ngày.")
        days.extend(range(start, end + 1))
        return " "

    remainder = _RANGE.sub(replace_range, message)
    days.extend(int(match[1]) for match in _REFERENCE.finditer(remainder))
    for match in _LIST.finditer(remainder):
        days.extend(int(number) for number in re.findall(r"\d+", match[0]))
    scope = normalize_scope(days)
    if scope and len(scope) > 50:
        raise ValueError("Chỉ có thể chọn tối đa 50 ngày.")
    return scope


def extract_mindmap_topic(message):
    remainder = _RANGE.sub(" ", message)
    remainder = _LIST.sub(" ", remainder)
    remainder = _REFERENCE.sub(" ", remainder)
    remainder = _TRIGGER.sub(" ", remainder)
    remainder = re.sub(r"[,:;.!?]+", " ", remainder)
    remainder = re.sub(r"\s+", " ", remainder).strip()
    remainder = _FILLER.sub(" ", remainder)
    return re.sub(r"\s+", " ", remainder).strip()[:200] or None


def parse_explicit_mindmap_scope(message):
    """Return a multi-day intent; preserve unknown days for API validation."""
    if not isinstance(message, str) or not _TRIGGER.search(message):
        return None
    days = []
    structured = False

    def replace_range(match):
        nonlocal structured
        structured = True
        start, end = map(int, match.groups())
        if start < 1 or end < start or end - start + 1 > 50:
            raise ValueError("Phạm vi ngày không hợp lệ; dùng ngày tăng dần, tối đa 50 ngày.")
        days.extend(range(start, end + 1))
        return " "

    def replace_list(match):
        nonlocal structured
        structured = True
        days.extend(int(number) for number in re.findall(r"\d+", match[0]))
        return " "

    remainder = _RANGE.sub(replace_range, message)
    remainder = _LIST.sub(replace_list, remainder)
    references = list(_REFERENCE.finditer(remainder))
    days.extend(int(match[1]) for match in references)
    if not structured and len(set(days)) < 2:
        return None
    scope = normalize_scope(days)
    if len(scope) > 50:
        raise ValueError("Chỉ có thể chọn tối đa 50 ngày.")
    remainder = _REFERENCE.sub(" ", remainder)
    remainder = _TRIGGER.sub(" ", remainder)
    remainder = re.sub(r"[,:;.!?]+", " ", remainder)
    remainder = re.sub(r"\s+", " ", remainder).strip()
    remainder = _FILLER.sub(" ", remainder)
    remainder = re.sub(r"\s+", " ", remainder).strip()
    remainder = re.sub(r"^(?:từ|đến|tới|và|&)\s*|\s*(?:từ|đến|tới|và|&)$", "", remainder, flags=re.I).strip()
    return {"day": None, "scope": scope, "topic": remainder or None}
