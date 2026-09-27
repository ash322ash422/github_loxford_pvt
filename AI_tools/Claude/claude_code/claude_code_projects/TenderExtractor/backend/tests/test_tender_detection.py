"""Unit tests for the deterministic tender keyword check."""
from app.services.tender_detection import looks_like_tender


def _pages(text: str) -> list[dict]:
    return [{"page_number": 1, "text": text}]


def test_matches_notice_keyword():
    assert looks_like_tender(_pages("NOTICE INVITING E-TENDER")) is True


def test_matches_nit_keyword_case_insensitively():
    assert looks_like_tender(_pages("nit no. 41/EE/E/PEED/2026-2027")) is True


def test_matches_tender_keyword():
    assert looks_like_tender(_pages("This document is a Tender for supply of goods.")) is True


def test_no_match_returns_false():
    assert looks_like_tender(_pages("Dear Sir, please find enclosed our quarterly report.")) is False


def test_nit_does_not_match_inside_unrelated_words():
    """Word-boundary matching: 'nit' must not match substrings inside
    'monitor', 'unit', 'definite', etc."""
    text = "Please monitor the unit and provide a definite schedule."
    assert looks_like_tender(_pages(text)) is False


def test_checks_across_multiple_pages():
    pages = [
        {"page_number": 1, "text": "Cover page, no keywords here."},
        {"page_number": 2, "text": "INDEX\n1. Notice Inviting Tender ... 3"},
    ]
    assert looks_like_tender(pages) is True
