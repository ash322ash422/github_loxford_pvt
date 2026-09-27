"""
Extracts specific page-number references (Terms & Conditions, Acceptable
Make, List of Documents to be Scanned & Uploaded) from the tender's
first few pages using an LLM. A fuzzy table match on "INDEX" is too
brittle across tenders - section wording and table layout vary, so the
LLM reads the raw OCR text and reports only what it actually finds.
"""
from __future__ import annotations

import json
from typing import Callable, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.callbacks.manager import get_openai_callback

from app import config
from app.services.llm import get_llm
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

TARGET_HEADING = "Index Page References"  # kept for logging parity with other *_data_service modules
MAX_PAGES_TO_SEARCH = config.INDEX_CHECK_PAGES

SYSTEM_PROMPT = """You are a precise information-extraction assistant. You will be given \
OCR text from the first few pages of an Indian government tender document (NIT). \
These pages typically contain an "INDEX" or table of contents listing each section \
of the tender along with the page number(s) where it appears.

Your job is to find the page number(s) for exactly three items:
1. "Terms and Conditions" (may also appear as "General Terms & Conditions", \
"Terms & Conditions", "Special Conditions", etc.)
2. "Acceptable Make" (may also appear as "List of Acceptable Makes", \
"Approved Makes", "Make of Material", etc.)
3. "List of Documents to be Scanned and Uploaded" (may also appear as \
"Documents to be scanned and uploaded", "List of Documents required to be \
uploaded", etc.)
4. "Schedule of  Quantities" (may also appear as \
"Schedule of work", "BOQ","Bill of Quantity","" etc.)

Rules:
- Only use information explicitly present in the provided text. Do not guess \
or infer a page number that isn't written down.
- If an item spans a page range (e.g. "44-48"), return the full range as a string.
- If an item is not present in the text, its value MUST be null. Never invent \
a page number.
- Respond with JSON only, no other text, no markdown code fences, matching \
exactly this schema:

{
  "terms_and_conditions_page": <string or null>,
  "acceptable_make_page": <string or null>,
  "documents_to_be_scanned_page": <string or null>,
  "schedule_of_quantity": <string or null>
}
"""


def _build_user_prompt(pages: list[dict]) -> str:
    excerpt = "\n\n".join(
        f"--- Page {p['page_number']} ---\n{p.get('text', '')}"
        for p in pages[:MAX_PAGES_TO_SEARCH]
    )
    return f"OCR text from the first {MAX_PAGES_TO_SEARCH} pages:\n\n{excerpt}"


def _call_llm(
    system_prompt: str,
    user_prompt: str,
    token_callback: Optional[Callable[[int], None]] = None,
) -> str:
    """
    Calls the shared LangChain chat model (see app.services.llm.get_llm).
    Must return the raw text of the model's response.
    """
    llm = get_llm()

    with get_openai_callback() as cb:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        total_tokens = cb.total_tokens
        logger.info("Total Tokens Usage (INDEX search): %d", total_tokens)

    if token_callback:
        token_callback(total_tokens)

    return response.content


def _parse_llm_response(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw.split("\n", 1)[-1]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON: {raw!r}") from e

    expected_keys = (
        "terms_and_conditions_page",
        "acceptable_make_page",
        "documents_to_be_scanned_page",
        "schedule_of_quantity",
    )
    return {key: data.get(key) for key in expected_keys}


def extract_data(pages: list[dict], token_callback: Optional[Callable[[int], None]] = None) -> dict:
    """
    Ask the LLM to locate the page numbers of Terms & Conditions,
    Acceptable Make, List of Documents to be Scanned & Uploaded, Schedule of Quantity
    from the first MAX_PAGES_TO_SEARCH pages of OCR text.

    Raises ValueError only if the LLM call itself fails or returns
    unparsable output. Individual fields being None is an expected, valid
    result (the LLM looked and didn't find that item) - not an error.

    token_callback, if given, is invoked once with the total token count
    used by this call (see app.pipeline.stages, which uses it to
    accumulate PipelineContext.token_count).
    """
    user_prompt = _build_user_prompt(pages)

    try:
        raw_response = _call_llm(SYSTEM_PROMPT, user_prompt, token_callback=token_callback)
    except Exception as e:
        raise ValueError(f"LLM call failed while extracting index page references: {e}") from e

    result = _parse_llm_response(raw_response)

    if all(v is None for v in result.values()):
        logger.warning(
            "LLM could not find any of the target sections in the first %d pages.",
            MAX_PAGES_TO_SEARCH,
        )

    return result


if __name__ == "__main__":
    # Quick manual test with fake OCR pages - hits the real LLM (needs valid
    # AZURE_OPENAI_* env vars). "Acceptable Make" is deliberately absent so
    # you can confirm the null-when-missing behavior actually works.
    fake_pages = [
        {
            "page_number": 1,
            "text": "GOVERNMENT OF INDIA\nCENTRAL PUBLIC WORKS DEPARTMENT\n"
                    "NOTICE INVITING TENDER\nNIT No. 41/EE/E/PEED/2026-2027\n"
                    "Name of Work: RMO Fire Alarm & Fire Fighting System.",
        },
        {
            "page_number": 2,
            "text": "INDEX\nSl.No.  Description  Page no.\n"
                    "1.  Cover Page  1\n"
                    "2.  Index  2\n"
                    "3.  Notice inviting e-tender  3\n"
                    "5.  List of Documents to be scanned and uploaded within the period of bid submission  8\n"
                    "13.  General Terms & Conditions  44-48\n"
                    "23.  Schedule of Quantities  66-69",
                    
        },
        {
            "page_number": 3,
            "text": "NOTICE INVITING E-TENDER\nEstimated Cost put to tender  Rs. 58,63,632.00\n"
                    "Earnest Money  Rs. 1,17,273.00\nPeriod of Completion  12 Months",
        },
    ]
 
    result = extract_data(fake_pages)
    print(json.dumps(result, indent=2))
 