"""
Sends OCR'd pages to the LLM in chunks and merges the partial results
into one flat dict of extracted fields.
"""
import json
from typing import Callable, Optional

from langchain_community.callbacks.manager import get_openai_callback

from app.services import llm as llm_service
from app.services.prompt import build_extraction_prompt
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

MAX_PAGES_TO_SEARCH_NIT = 4

def extract_chunk(
    pages: list,
    fields: list,
    token_callback: Optional[Callable[[int], None]] = None,
) -> dict:

    llm = llm_service.get_llm()
    prompt = build_extraction_prompt(pages=pages, fields=fields)
    logger.info(".....Sending %s pages to LLM for NIT extraction", len(pages))

    with get_openai_callback() as cb:
        response = llm.invoke(prompt)
        total_tokens = cb.total_tokens
        logger.info("Total Tokens Usage (NIT): %d", total_tokens)

    if token_callback:
        token_callback(total_tokens)

    return json.loads(response.content)

def merge_results(results: list) -> dict:
    """First non-empty value wins across chunks."""
    final = {}
    for partial in results:
        for key, value in partial.items():
            if value and not final.get(key):
                final[key] = value
    return final


def extract_document(
    document_data: dict,
    fields: list,
    token_callback: Optional[Callable[[int], None]] = None,
) -> dict:

    if document_data is None:
        logger.error("Received None for document_data.")
        return {}

    # NIT data is present only in the first few pages. So only send these.
    nit_pages = document_data.get("pages", [])[:MAX_PAGES_TO_SEARCH_NIT]
    
    # 1. Guard Clause for Empty Input
    if not nit_pages:
        logger.warning("No pages found in document_data. Skipping extraction.")
        return {}

    # 2. Safe Logging for the Target Pages
    start_page = nit_pages[0].get("page_number", 1)
    end_page = nit_pages[-1].get("page_number", len(nit_pages))
    logger.info("Extracting NIT data from pages %s-%s", start_page, end_page)
    
    # 3. Process the Complete 4-page Target Block
    result = extract_chunk(nit_pages, fields, token_callback=token_callback)
    
    if not result:
        return {}
        
    return result
