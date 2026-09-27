# tender_detection.py
"""
Cheap, deterministic check for whether a document is actually a tender, run
against the first few OCR'd pages before the pipeline commits to a
full-document OCR pass. Word-boundary, case-insensitive match against
TENDER_KEYWORDS - good enough to filter out non-tender uploads without
spending an LLM call on documents that already clearly aren't tenders.
"""
from __future__ import annotations

import re

TENDER_KEYWORDS = ("notice", "tender", "nit")

_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(keyword) for keyword in TENDER_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def looks_like_tender(pages: list[dict], pattern: re.Pattern = _PATTERN) -> bool:
    """True if any TENDER_KEYWORDS word appears in the given pages' text."""
    text = "\n".join(page.get("text", "") for page in pages)
    return bool(pattern.search(text))
