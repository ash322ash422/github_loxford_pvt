"""
Wraps Azure AI Document Intelligence: turns raw PDF bytes into a
structured {"pages": [...]} document with text, tables and key/value
pairs per page.
"""
import io
from typing import Optional

import pdfplumber
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def create_document_client(endpoint: str, key: str) -> DocumentAnalysisClient:
    return DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))


def validate_pdf_is_digital(pdf_bytes: bytes, sample_pages: int = 5) -> bool:
    """Raises ValueError if none of the first `sample_pages` pages contain selectable text."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages_to_check = min(len(pdf.pages), sample_pages)

        for i in range(pages_to_check):
            text = pdf.pages[i].extract_text()
            if text and len(text.strip()) > 10:
                return True

    raise ValueError(
        f"The PDF appears to be a scanned image - no selectable text found "
        f"in the first {min(sample_pages, sample_pages)} pages."
    )


def analyze_document_from_bytes(
    document_bytes: bytes,
    endpoint: str,
    key: str,
    model_name: str,
    pages: Optional[str] = None,
):
    """
    pages, if given, limits analysis (and billing) to those pages only -
    e.g. "1-3". Forwarded only when set so the full-document call path is
    unchanged from before this parameter existed.
    """
    client = create_document_client(endpoint, key)
    kwargs = {"pages": pages} if pages else {}
    poller = client.begin_analyze_document(model_id=model_name, document=document_bytes, **kwargs)
    return poller.result()


def _extract_pages(result) -> list:
    pages = []
    for page in result.pages:
        page_text = "\n".join(line.content for line in page.lines)
        selection_marks = [
            {"state": mark.state, "confidence": mark.confidence}
            for mark in (getattr(page, "selection_marks", None) or [])
        ]
        pages.append(
            {
                "page_number": page.page_number,
                "text": page_text,
                "width": page.width,
                "height": page.height,
                "unit": page.unit,
                "angle": page.angle,
                "tables": [],
                "key_value_pairs": [],
                "paragraphs": [],
                "headings": [],
                "selection_marks": selection_marks,
            }
        )
    return pages

def _attach_paragraphs(result, pages: list) -> list:
    """
    Attach each paragraph to its page, including Document Intelligence's
    role classification. `headings` is a convenience list containing just
    the "title"/"sectionHeading" paragraphs on that page — use it to find
    sections directly instead of fuzzy-matching raw text.
    """
    for paragraph in getattr(result, "paragraphs", None) or []:
        if not paragraph.bounding_regions:
            continue

        role = paragraph.role  # None for ordinary body paragraphs
        seen_pages = set()
        for region in paragraph.bounding_regions:
            page_no = region.page_number
            if page_no in seen_pages:
                continue
            seen_pages.add(page_no)

            pages[page_no - 1]["paragraphs"].append({"content": paragraph.content, "role": role})
            if role in ("title", "sectionHeading"):
                pages[page_no - 1]["headings"].append(paragraph.content)

    return pages


def _attach_tables(result, pages: list) -> list:
    for table in result.tables:
        if not table.bounding_regions:
            continue

        page_no = table.bounding_regions[0].page_number
        rows = [[""] * table.column_count for _ in range(table.row_count)]

        for cell in table.cells:
            rows[cell.row_index][cell.column_index] = cell.content

        pages[page_no - 1]["tables"].append(rows)

    return pages


def _attach_key_value_pairs(result, pages: list) -> list:
    if not result.key_value_pairs:
        return pages

    for kv in result.key_value_pairs:
        if not kv.key.bounding_regions:
            continue

        page_no = kv.key.bounding_regions[0].page_number
        pages[page_no - 1]["key_value_pairs"].append(
            {"key": kv.key.content, "value": kv.value.content if kv.value else ""}
        )

    return pages


def extract_document_data(result) -> dict:
    """Converts a Document Intelligence result into {"pages": [...]}."""
    pages = _extract_pages(result)
    pages = _attach_paragraphs(result, pages)
    pages = _attach_tables(result, pages)
    pages = _attach_key_value_pairs(result, pages)
    return {"pages": pages}