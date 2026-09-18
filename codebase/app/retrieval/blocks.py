"""Rejoin PDF paragraphs split into consecutive native text blocks."""

import re

from app.viewer.evidence import normalized_bbox


def merge_continuations(blocks, native_text):
    """Keep exact text and a combined box only for verified paragraph continuations.

    The first block ID identifies the resulting passage. Never cross columns,
    new bullets, sentence boundaries, or the footer, or invent text ordering.
    """
    normalized_text = " ".join(native_text.split())
    merged = []
    for original in blocks:
        block = dict(original)
        if merged:
            previous = merged[-1]
            first_box = normalized_bbox(previous.get("bbox"))
            next_box = normalized_bbox(block.get("bbox"))
            first_text, next_text = previous.get("text", ""), block.get("text", "")
            quote = first_text + "\n" + next_text
            continuation = (
                first_box is not None and next_box is not None
                and first_text.strip() and next_text.strip() and len(quote) <= 1200
                and not re.search(r"[.!?;:…]\s*$", first_text)
                and not re.match(r"\s*(?:[•■▪●▶*]|[-–]\s|copyright\b|©|all rights reserved\b)", next_text, re.I)
                and next_box[1] < 0.94
                and abs(next_box[0] - first_box[0]) <= 0.08
                and min(first_box[2], next_box[2]) > max(first_box[0], next_box[0])
                and -0.005 <= next_box[1] - first_box[3] <= max(
                    0.012, 0.75 * min(first_box[3] - first_box[1], next_box[3] - next_box[1]))
                and " ".join(quote.split()) in normalized_text
            )
            if continuation:
                previous["text"] = quote
                previous["bbox"] = [min(first_box[0], next_box[0]), min(first_box[1], next_box[1]),
                                    max(first_box[2], next_box[2]), max(first_box[3], next_box[3])]
                continue
        merged.append(block)
    return merged
