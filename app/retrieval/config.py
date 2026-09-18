"""Defensive environment parsing for optional retrieval upgrades."""
import os


def enabled(name, default=True):
    return os.getenv(name, str(default)).strip().lower() not in {"false", "0", "no", "off"}


def integer(name, default, minimum=1):
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def retrieval_text(slide):
    value = slide.get("retrieval_text")
    return value if isinstance(value, str) and value.strip() else slide.get("text", "")


def visual_evidence_text(slide):
    """Use successful descriptions as visual evidence, separate from PDF quotes."""
    analysis = slide.get("visual_analysis")
    if not isinstance(analysis, dict) or analysis.get("status") != "success":
        return ""
    summary = analysis.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return ""
    parts = [summary]
    for field, label in (("relationships", "Relationships"), ("visible_text_not_in_pdf", "Visible text")):
        values = analysis.get(field)
        if isinstance(values, list) and all(isinstance(value, str) for value in values) and values:
            parts.append(label + ": " + "; ".join(values))
    return "\n".join(parts)
