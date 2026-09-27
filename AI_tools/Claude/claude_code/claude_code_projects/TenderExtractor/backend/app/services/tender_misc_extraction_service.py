
# To run this as standalone: python -m app.services.tender_extraction_service
from __future__ import annotations

import json
import re
from typing import Callable, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, model_validator
from langchain_community.callbacks.manager import get_openai_callback
    
from app.services.llm import get_llm
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# No hard page cap by default. In real NITs, these sections routinely start
# well past the first few pages (in three sample tenders they started on
# pages 6, 9, and 11, and one ran through page 13) so truncating early
# silently drops data. Override via extract_data(..., max_pages=N) only if
# you know the section you need is near the front and want to save tokens.
DEFAULT_MAX_PAGES: Optional[int] = None

# Rough safety valve: warn if the OCR text is large enough that a single
# call might approach typical context limits. This does NOT chunk for you -
# it just tells you loudly instead of silently truncating or erroring deep
# inside the model call. Tune to your model's actual context window.
WARN_CHAR_THRESHOLD = 400_000


SYSTEM_PROMPT = """
You are a precise information-extraction assistant. You are an expert in extracting key data from Indian
government tender files.

You will be given JSON-derived OCR text from a PDF of an Indian government tender document (NIT), broken
into pages. Each page may also include a separate list of tables already parsed into rows and columns -
use those when present instead of re-parsing table-like text yourself, since they are more reliable.

Your job is to extract exactly three items:

1. "Terms and Conditions" - may appear under headings such as "General Terms & Conditions",
   "Terms & Conditions", "Special Conditions", "General Conditions", etc. A document may contain more than
   one such section under different headings (e.g. both "Terms & Conditions" and "General Conditions") -
   capture each as a separate section. If a small table (e.g. example item rates) appears embedded within
   or right after a Terms and Conditions section, that table belongs together with those clauses, in this
   same "terms_and_conditions" field/section - put its rows in that section's `tables`, not in a separate
   section.
   BUT a broader heading (e.g. "Maintenance of Fire-Fighting System", "Special Conditions for maintenance
   tenders") that mixes genuine procedural clauses with OTHER embedded content is not entirely Terms and
   Conditions - capture only the genuine clauses as items, and never capture any of the following, even
   though they're nested under that same heading:
   - A signature/approval block - a "table" whose columns are just designations/job-titles (e.g.
     "Assistant Engineer (E) (P)" / "Executive Engineer (E)") with an office address or nothing else as the
     row content. This is a place for two people to sign, not data - never extract it, in any field.
   - A scope-of-work / job-description table (e.g. columns "S.No." / "Work Involved", listing maintenance
     tasks to be performed) - this describes WHAT work is done, not a term or condition of the contract,
     and doesn't belong in any of the three items - omit it entirely.
   - An equipment/inventory listing table (e.g. "Item" / location columns / "Total" / "Unit", counting
     installed equipment) - an inventory annexure, not a term or condition - omit it entirely.
   If the same scope-of-work or inventory table also appears as its own standalone heading elsewhere in the
   document (e.g. titled after its own caption, like "Maintenance Job Involved in Fire Fighting &
   Sprinklers"), that's the exact same content repeated - still omit it, don't create a section for it
   either.

2. "Acceptable Make" - may appear under headings such as "List of Acceptable Makes", "Approved Makes",
   "Make of Material", etc. This is sometimes a standalone table/section, and sometimes embedded inside a
   numbered clause of the Terms and Conditions (e.g. "the contractor shall use any of the following makes:
   a) MS Pipe: Jindal/Tata ..."). Extract it as its own field either way. It must genuinely OFFER a choice
   of brands/manufacturers as acceptable options for a material or equipment item - a brand name that only
   appears incidentally in unrelated content (e.g. named in a blank "Willingness Certificate" annexure/
   proforma template, a warranty card, an OEM authorization letter, or any other document to be filled and
   signed) is NOT Acceptable Make, even though a brand/company name is present. Annexures and proforma
   templates (blank certificates with signature blocks, meant to be filled in and submitted) are not
   Acceptable Make, Terms and Conditions, or the third item below either - skip them entirely rather than
   summarizing what they're about into a fabricated list.

3. "List of Documents to be Scanned and Uploaded" - may appear as "Documents to be scanned and uploaded",
   "List of Documents required to be uploaded", etc. A document may contain more than one such list for
   different bidder categories (e.g. one list "for CPWD registered contractors" and another "for Non-CPWD
   agencies") - capture each as a separate section.

Rules:
- Only use information explicitly present in the provided text. Do not infer or fabricate content. Every
  item's "text" must be copied from the source, not a summary or paraphrase you composed - if you find
  yourself describing what a page is about rather than quoting it, stop and check whether that page even
  belongs to one of the three items at all (annexures/proforma templates usually don't, see item 2 above).
- Any of the three items may span multiple pages and/or multiple distinct headings - merge content for the
  same logical item together, but keep distinct headings as distinct sections.
- Never attach a heading from one page to table content found on a different page unless the same heading
  text (or a close variant) is genuinely repeated directly above/near equivalent table content on both
  pages. A heading with no table directly beneath it on its own page (e.g. a cover/index page that just
  names sections) must never be borrowed as the heading for an unrelated table found elsewhere.
- Preserve original numbering/lettering exactly as printed (e.g. "1.", "(iii)", "a)"). If an item has no
  numbering in the source, leave the number field null.
- CRITICAL for tables: every row must have exactly as many cells as there are columns - never omit, merge,
  or reorder a cell, even if its value is a lone number, is blank, or is annotated with an OCR
  selection-mark artifact (e.g. ":selected:"). If a cell's true content is genuinely blank, still include it
  as an empty string rather than skipping it and shifting every later cell in that row to the left. When a
  page supplies an already-parsed table block (`[Page N parsed table K]`), copy it cell-for-cell exactly as
  given rather than re-reading the raw text above it - it is more reliable than your own re-parsing, and
  dropping even one cell (e.g. a row's serial number) misaligns every other value in that row.
- Preserve footnotes/notes attached to a section (e.g. "Note: ...") separately from the numbered items.
- If an item is not present anywhere in the provided text, mark it as not present and leave its sections
  list empty - do not guess.
- Record which page number(s) each section's content came from.
"""


# --------------------------------------------------------------------------
# Structured output schema
#
# Generic enough to cover every shape we've actually seen: a single plain
# numbered list (tender 1), a single very long numbered list split across
# many pages (tender 2), two differently-headed numbered lists for the same
# field (tender 3's "Terms & Conditions" + "General Conditions", and its two
# "Documents" lists for CPWD vs non-CPWD bidders), and a table that's either
# standalone or embedded inside another clause.
# --------------------------------------------------------------------------

class ExtractedTable(BaseModel):
    caption: Optional[str] = Field(
        None, description="Short label for the table if the source gives one, else null."
    )

    columns: list[str] = Field(
        default_factory=list, description="Column headers, in order, exactly as printed."
    )

    rows: list[list[str]] = Field(
        default_factory=list, description="Table rows; each row's cells align with `columns`."
    )

    @model_validator(mode="after")
    def _warn_on_ragged_rows(self) -> "ExtractedTable":
        """
        The LLM is asked to re-type tables cell-for-cell (see SYSTEM_PROMPT's
        "CRITICAL for tables" rule), but occasionally drops or duplicates a
        cell anyway - typically on a row with an OCR selection-mark artifact
        or heavily wrapped text - which silently shifts every later cell in
        that row into the wrong column in the exported Excel. There's no
        reliable way to guess which cell is missing and auto-correct it here,
        so this just makes the problem loud instead of silent: check this
        table's caption/row content against logs/{job_id}/ocr.json's raw
        parsed table for the real values if you see this warning.
        """
        expected = len(self.columns)
        if not expected:
            return self
        for i, row in enumerate(self.rows, start=1):
            if len(row) != expected:
                logger.warning(
                    "Table %r: row %d has %d cell(s) but there are %d column(s) (%s) - "
                    "likely misaligned in the exported Excel. Row content: %r",
                    self.caption or "(untitled)", i, len(row), expected, self.columns, row,
                )
        return self


class ExtractedItem(BaseModel):
    number: Optional[str] = Field(
        None, description="Numbering/lettering exactly as printed, e.g. '1.', '(iii)', 'a)'. Null if unnumbered."
    )
    text: str = Field(description="Verbatim text of this clause/item/document requirement.")


class ExtractedSection(BaseModel):
    heading: Optional[str] = Field(
        None,
        description=(
            "Exact heading text this content appears under, e.g. 'General Terms & Conditions', "
            "'List of Documents for CPWD Reg. Contractors'. Null if the content has no heading of its own "
            "(e.g. a make list embedded inside a Terms & Conditions clause)."
        ),
    )
    source_pages: list[int] = Field(
        default_factory=list, description="Page numbers this section's content was found on."
    )
    items: list[ExtractedItem] = Field(
        default_factory=list, description="Numbered/lettered/plain list items, in original order."
    )
    tables: list[ExtractedTable] = Field(
        default_factory=list, description="Tables belonging to this section, if any."
    )
    notes: list[str] = Field(
        default_factory=list, description="Footnotes/asterisked notes/caveats attached to this section."
    )


class ExtractedField(BaseModel):
    present: bool = Field(description="True if this item was found anywhere in the provided text.")
    sections: list[ExtractedSection] = Field(
        default_factory=list,
        description="One entry per distinct heading/variant found. Empty when `present` is False.",
    )


class TenderExtraction(BaseModel):
    terms_and_conditions: ExtractedField
    acceptable_make: ExtractedField
    documents_to_be_scanned_and_uploaded: ExtractedField


def _build_user_prompt(pages: list[dict], max_pages: Optional[int]) -> str:
    selected = pages if max_pages is None else pages[:max_pages]

    blocks = []
    for p in selected:
        block = [f"--- Page {p['page_number']} ---", p.get("text", "")]
        tables = p.get("tables") or []
        for i, table in enumerate(tables, start=1):
            if not table:
                continue
            block.append(f"[Page {p['page_number']} parsed table {i}]")
            block.append(json.dumps(table, ensure_ascii=False))
        blocks.append("\n".join(block))

    excerpt = "\n\n".join(blocks)

    if len(excerpt) > WARN_CHAR_THRESHOLD:
        logger.warning(
            "OCR excerpt is %d characters across %d pages; this may approach the model's "
            "context limit in a single call. Consider chunking by page ranges if you see "
            "truncated or failed responses.",
            len(excerpt),
            len(selected),
        )

    return f"OCR text (with parsed tables where available) from {len(selected)} page(s):\n\n{excerpt}"


def _call_llm_structured(
    system_prompt: str,
    user_prompt: str,
    token_callback: Optional[Callable[[int], None]] = None,
) -> TenderExtraction:
    logger.info("Using _call_llm_structured (native structured output) for this LLM call.")
    llm = get_llm()
    structured_llm = llm.with_structured_output(TenderExtraction)

    with get_openai_callback() as cb:
        response = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        total_tokens = cb.total_tokens
        logger.info("Total Tokens Usage: %d", total_tokens)

    if token_callback:
        token_callback(total_tokens)

    # Some langchain backends return the pydantic model directly; others
    # return a dict-like object depending on configuration.
    if isinstance(response, TenderExtraction):
        return response

    return TenderExtraction.model_validate(response)


def _call_llm_fallback(
    system_prompt: str,
    user_prompt: str,
    token_callback: Optional[Callable[[int], None]] = None,
) -> TenderExtraction:
    """
    Fallback path for LLM backends that don't support with_structured_output.
    Embeds the JSON schema in the prompt and parses/validates the raw
    response, tolerating code-fenced responses.
    """
    logger.info("Using _call_llm_fallback (raw JSON parsing - this LLM backend has no with_structured_output).")
    llm = get_llm()
    schema_hint = (
        "\n\nRespond with ONLY a single JSON object matching exactly this schema "
        "(no markdown fences, no commentary):\n"
        f"{json.dumps(TenderExtraction.model_json_schema(), indent=2)}"
    )

    with get_openai_callback() as cb:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt + schema_hint),
        ])
        total_tokens = cb.total_tokens
        logger.info("Total Tokens Usage: %d", total_tokens)

    if token_callback:
        token_callback(total_tokens)

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw.split("\n", 1)[-1]
    try:
        return TenderExtraction.model_validate_json(raw)
    except Exception as e:
        raise ValueError(f"LLM did not return JSON matching the expected schema: {raw!r}") from e


def _attach_missing_terms_tables_from_raw_ocr(extraction: TenderExtraction, pages: list[dict]) -> TenderExtraction:
    """
    Deterministic backstop for a third failure mode on the same kind of
    page: sometimes the LLM correctly classifies a Terms and Conditions
    section but simply omits a small table that's actually there - not a
    misclassification like the other two filters above handle, just
    outright under-extraction, non-deterministic across calls, so no
    prompt wording reliably prevents it. If a terms_and_conditions section
    has no table of its own, but one of its own source_pages has a
    Document-Intelligence-parsed table that no other section in this
    extraction has already claimed, attach that raw table directly -
    copied verbatim from Document Intelligence's own reliable parse
    (proven correct earlier - see the row-misalignment fix), never
    re-typed by the LLM, so there's no risk of it being wrong.
    """
    field = extraction.terms_and_conditions
    if not field.present:
        return extraction

    claimed_rows = {
        tuple(tuple(row) for row in table.rows)
        for other_field in TenderExtraction.model_fields
        for section in getattr(extraction, other_field).sections
        for table in section.tables
    }
    pages_by_number = {p["page_number"]: p for p in pages}

    for section in field.sections:
        if section.tables:
            continue

        for page_number in section.source_pages:
            page = pages_by_number.get(page_number)
            for raw_table in (page or {}).get("tables") or []:
                if not raw_table or len(raw_table) < 2:
                    continue
                header, *rows = raw_table
                row_key = tuple(tuple(row) for row in rows)
                if row_key in claimed_rows:
                    continue

                section.tables.append(ExtractedTable(columns=header, rows=rows))
                claimed_rows.add(row_key)
                logger.warning(
                    "Terms and Conditions: attached a table from page %d directly from Document "
                    "Intelligence's raw parse (the LLM's extraction omitted it) - section %r.",
                    page_number, section.heading,
                )

    return extraction


_SIGNATURE_BLOCK_COLUMN_HINT = re.compile(r"engineer|officer|authority|signatory|signature", re.IGNORECASE)
_SCOPE_OF_WORK_COLUMN_HINT = re.compile(r"work involved|job involved|scope of work", re.IGNORECASE)


def _is_signature_block_table(table: ExtractedTable) -> bool:
    """A table whose columns are ALL designation/job-title labels (e.g.
    "Assistant Engineer (E) (P)" / "Executive Engineer (E)") is a place
    for two people to sign, not data - a real data table wouldn't have
    every single column header be a job title."""
    return (
        0 < len(table.columns) <= 3
        and all(_SIGNATURE_BLOCK_COLUMN_HINT.search(col) for col in table.columns)
    )


def _is_scope_of_work_table(table: ExtractedTable) -> bool:
    """Columns like "S.No." / "Work Involved" describe WHAT work is done,
    not a term or condition of the contract."""
    return any(_SCOPE_OF_WORK_COLUMN_HINT.search(col) for col in table.columns)


def _is_inventory_table(table: ExtractedTable) -> bool:
    """Columns including both a bare "Item" and a bare "Total" (e.g.
    "S.No." / "Item" / <location columns> / "Total" / "Unit") is an
    equipment inventory annexure, not a term or condition."""
    normalized = {col.strip().lower() for col in table.columns}
    return "item" in normalized and "total" in normalized


def _drop_non_terms_tables_from_terms_and_conditions(extraction: TenderExtraction) -> TenderExtraction:
    """
    Deterministic backstop for a fourth failure mode: the LLM sometimes
    sweeps content that's nested under (or near) a Terms and Conditions
    heading into that field even though it isn't actually a term or
    condition - specifically signature blocks, scope-of-work/job-
    description tables, and equipment inventory tables, all observed in
    the same real document. Each has a distinct, checkable column-header
    shape (see the three `_is_*_table` helpers above), so these get
    dropped here rather than relying solely on the SYSTEM_PROMPT's
    exclusion rule.
    """
    field = extraction.terms_and_conditions
    if not field.present:
        return extraction

    kept_sections = []
    for section in field.sections:
        kept_tables = []
        for table in section.tables:
            if _is_signature_block_table(table):
                reason = "a signature block (columns are just designations)"
            elif _is_scope_of_work_table(table):
                reason = "a scope-of-work/job-description table"
            elif _is_inventory_table(table):
                reason = "an equipment inventory table"
            else:
                kept_tables.append(table)
                continue
            logger.warning(
                "Terms and Conditions: dropped a table from section %r (pages %s) - %s, not a term or "
                "condition.",
                section.heading, section.source_pages, reason,
            )

        if kept_tables or section.items or section.notes:
            kept_sections.append(section.model_copy(update={"tables": kept_tables}))

    extraction.terms_and_conditions = ExtractedField(present=bool(kept_sections), sections=kept_sections)
    return extraction


def _extract_chunk(
    pages: list[dict],
    max_pages: Optional[int],
    token_callback: Optional[Callable[[int], None]],
) -> TenderExtraction:
    user_prompt = _build_user_prompt(pages, max_pages)
    try:
        llm = get_llm()
        if hasattr(llm, "with_structured_output"):
            extraction = _call_llm_structured(SYSTEM_PROMPT, user_prompt, token_callback=token_callback)
        else:
            extraction = _call_llm_fallback(SYSTEM_PROMPT, user_prompt, token_callback=token_callback)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"LLM call failed while extracting tender data: {e}") from e

    extraction = _attach_missing_terms_tables_from_raw_ocr(extraction, pages)
    return _drop_non_terms_tables_from_terms_and_conditions(extraction)


def _normalize_heading(heading: Optional[str]) -> Optional[str]:
    if heading is None:
        return None
    return " ".join(heading.split()).strip().lower()


def _merge_extractions(chunks: list[TenderExtraction]) -> TenderExtraction:
    """
    Concatenate sections for each field across chunk results, re-merging
    sections whose heading (normalized: whitespace-collapsed, case-insensitive)
    matches across batches. Unheaded sections (heading=None) are never merged
    with each other, since there's no reliable way to tell if they're the
    same logical section or unrelated content that happened to lack a heading.
    """
    merged = {}

    for field_name in TenderExtraction.model_fields:
        present = any(getattr(c, field_name).present for c in chunks)

        # key -> merged ExtractedSection; key is normalized heading, or a
        # unique sentinel per unheaded section so they never collide.
        by_key: dict[object, ExtractedSection] = {}
        order: list[object] = []
        unheaded_counter = 0

        for c in chunks:
            for section in getattr(c, field_name).sections:
                norm = _normalize_heading(section.heading)
                if norm is None:
                    unheaded_counter += 1
                    key = ("unheaded", unheaded_counter)
                else:
                    key = ("heading", norm)

                if key not in by_key:
                    by_key[key] = ExtractedSection(
                        heading=section.heading,
                        source_pages=list(section.source_pages),
                        items=list(section.items),
                        tables=list(section.tables),
                        notes=list(section.notes),
                    )
                    order.append(key)
                else:
                    existing = by_key[key]
                    existing.source_pages = sorted(set(existing.source_pages) | set(section.source_pages))
                    existing.items.extend(section.items)
                    existing.tables.extend(section.tables)
                    existing.notes.extend(section.notes)

        sections = [by_key[k] for k in order]
        merged[field_name] = ExtractedField(present=present, sections=sections)

    return TenderExtraction(**merged)


def extract_data(
    pages: list[dict],
    max_pages: Optional[int] = DEFAULT_MAX_PAGES,
    token_callback: Optional[Callable[[int], None]] = None,
    page_chunk_size: Optional[int] = None,
) -> dict:
    """
    Extract Terms and Conditions, Acceptable Make, and List of Documents to
    be Scanned and Uploaded from OCR page data, returning a JSON-ready dict
    matching the TenderExtraction schema. (Schedule of Quantity is handled
    separately - see tender_soq_extract_service.py - since it lives in a
    predictable spot near the end of the document and benefits from its own
    focused, narrow-page-range LLM call rather than being found by scanning
    everything alongside these three.)

    Each of the three top-level fields is an object of the form:
        {"present": bool, "sections": [ {heading, source_pages, items, tables, notes}, ... ]}

    A field with "present": false means the LLM looked and genuinely could
    not find that item anywhere in the supplied pages - that is an expected,
    valid result, not an error. This function raises ValueError only if the
    LLM call itself fails or its output can't be validated against the
    schema.

    The output is designed to convert cleanly to Excel later: iterate
    top-level fields -> sections -> items/tables, writing one sheet per
    field (as done for these three tenders already) or one row block per
    section within a sheet.

    token_callback, if given, is invoked once per LLM call with the total
    token count used by that call (see app.pipeline.stages, which uses it
    to accumulate PipelineContext.token_count).

    page_chunk_size, if given, splits `pages` into batches of that many
    pages, calls the LLM once per batch, and merges results by
    concatenating each field's `sections` list across batches - re-merging
    sections whose heading matches across batches (see _merge_extractions).
    If None (default), all pages go in one call.
    """
    selected = pages if max_pages is None else pages[:max_pages]

    if not page_chunk_size:
        logger.info("Extracting %d page(s) in a single LLM call.", len(selected))
        extraction = _extract_chunk(selected, None, token_callback)
        result = extraction.model_dump(mode="json")
        if not any(result[key]["present"] for key in result):
            logger.warning("LLM could not find any of the three target sections in %d page(s).", len(selected))
        return result

    batches = [selected[i:i + page_chunk_size] for i in range(0, len(selected), page_chunk_size)]
    total_batches = len(batches)
    logger.info("Extracting %d page(s) in %d batch(es) of up to %d pages each.", len(selected), total_batches, page_chunk_size)

    chunk_results: list[TenderExtraction] = []
    for i, batch in enumerate(batches, start=1):
        first_page, last_page = batch[0]["page_number"], batch[-1]["page_number"]
        logger.info("Batch %d/%d: sending pages %d-%d (%d pages)...", i, total_batches, first_page, last_page, len(batch))

        def batch_token_callback(tokens: int, _i=i, _total=total_batches) -> None:
            logger.info("Batch %d/%d: used %d tokens.", _i, _total, tokens)
            if token_callback:
                token_callback(tokens)

        extraction = _extract_chunk(batch, None, batch_token_callback)
        chunk_results.append(extraction)

        found = [k for k, v in extraction.model_dump(mode="json").items() if v["present"]]
        logger.info("Batch %d/%d done: found=%s", i, total_batches, found or "none")

    merged = _merge_extractions(chunk_results)
    result = merged.model_dump(mode="json")

    if not any(result[key]["present"] for key in result):
        logger.warning("LLM could not find any target sections across %d page(s), %d batch(es).", len(selected), total_batches)
    else:
        logger.info("Merge complete: %d page(s), %d batch(es).", len(selected), total_batches)

    return result


if __name__ == "__main__":
    # Quick manual test with fake OCR pages - hits the real LLM (needs valid
    # AZURE_OPENAI_* env vars, or whatever get_llm() is configured for).
    # "Acceptable Make" is deliberately absent so you can confirm the
    # not-present behavior actually works, and one clause is deliberately
    # numbered with a letter to check numbering preservation.

    fake_pages = [
        {
            "page_number": 1,
            "text": "GOVERNMENT OF INDIA\nCENTRAL PUBLIC WORKS DEPARTMENT\n"
            "NOTICE INVITING TENDER\nNIT No. 41/EE/E/PEED/2026-2027\n"
            "Name of Work: RMO Fire Alarm & Fire Fighting System.",
            "tables": [],
        },
        {
            "page_number": 5,
            "text": "List of Documents to be scanned and uploaded within the period of bid submission:\n"
            "1. Treasury Challan / Demand Draft against EMD.\n"
            "2. Copy of receipt for deposition of original EMD.\n"
            "3. Enlistment Order of the Contractor.",
            "tables": [],
        },
        {
            "page_number": 6,
            "text": "TERMS AND CONDITIONS\n"
            "1. Materials shall be got approved from the Engineer-in-Charge before use at site.\n"
            "2. Any damages done to the building shall be made good by the contractor.\n"
            "S.No. Description of Items Unit Rate",
            "tables": [
                [
                    ["S.No.", "Description of Items", "Unit", "Rate"],
                    ["1", "2x1.5 sq.mm fire alarm armored cable", "P/Mtrs", "30"],
                    ["2", "Addressable photo thermal detector", "Each", "90"],
                ]
            ],
        },
    ]
    
    
    # path = r"C:\Users\hi\Desktop\projects\python_projects\tutorial\play_langchain_llamaindex_langgraph\TenderExtractor\cache\01_tender_mini_version.ocr.json"
    # with open(path, "r", encoding="utf-8") as f:
    #         documents = json.load(f)
    # # print(documents['pages'])
    
    pages = fake_pages # documents['pages'] # or fake_pages
    
    result = extract_data(pages)
    print(json.dumps(result, indent=2))
