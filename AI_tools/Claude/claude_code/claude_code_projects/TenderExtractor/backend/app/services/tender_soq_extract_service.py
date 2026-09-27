# tender_soq_extract_service.py
"""
Extracts Schedule of Quantity (a.k.a. Schedule of Work, Bill of
Quantities/BOQ) from OCR page data - standalone from
tender_misc_extraction_service.py's three fields (Terms and Conditions,
Acceptable Make, Documents to be Scanned and Uploaded), following the same
extract-service/export-service split used for NIT data
(tender_nit_extract_service.py / tender_nit_export_excel.py).

Schedule of Quantity used to be a fourth field on that shared extraction
call, scanning the whole document alongside the other three - but it lives
in a predictable spot (the LAST few pages) in practice, and sharing one
big multi-purpose call with everything else meant it kept getting
misattributed with unrelated content found elsewhere in the document. This
module gets its own narrow, focused call instead: only the last
config.SOQ_LAST_PAGES pages, extracting exactly one thing.

To run this as standalone: python -m app.services.tender_soq_extract_service
"""
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

TARGET_HEADING = "Schedule of Quantity"

SYSTEM_PROMPT = """
You are a precise information-extraction assistant. You are an expert in extracting key data from Indian
government tender files.

You will be given JSON-derived OCR text from the LAST few pages of a PDF of an Indian government tender
document (NIT), broken into pages. Each page may also include a separate list of tables already parsed
into rows and columns - use those when present instead of re-parsing table-like text yourself, since they
are more reliable.

Your only job is to extract the "Schedule of Quantity" - it may appear under headings such as "Schedule of
Quantities", "Schedule of Work", "Bill of Quantities", "BOQ", "Schedule of Rates", etc. It is usually a
large tabular section listing items with columns such as S.No./Item No., Description of Item/Work, Unit,
Quantity, Rate, and Amount. Extract it as one or more tables (use multiple tables if the source splits it
into distinct headed sub-schedules, e.g. by trade or section) - preserve every row and column exactly as
printed rather than summarizing or flattening it into prose.

A table only qualifies as Schedule of Quantity if it has an explicit Quantity (or "Qty") column - that is
what makes it a schedule of QUANTITY. If none of the supplied pages contain such a table, mark it as not
present and leave sections empty - do not guess, and do not force-fit an unrelated table (e.g. a small
rate table with no Quantity column, or a signature block) into this field just because it's the only table
around.

Rules:
- Only use information explicitly present in the provided text. Do not infer, fabricate, or summarize -
  every cell's text must be copied from the source, not composed by you.
- CRITICAL for tables: every row must have exactly as many cells as there are columns - never omit, merge,
  or reorder a cell, even if its value is a lone number, is blank, or is annotated with an OCR
  selection-mark artifact (e.g. ":selected:"). If a cell's true content is genuinely blank, still include it
  as an empty string rather than skipping it and shifting every later cell in that row to the left. When a
  page supplies an already-parsed table block (`[Page N parsed table K]`), copy it cell-for-cell exactly as
  given rather than re-reading the raw text above it - it is more reliable than your own re-parsing.
- Preserve footnotes/notes attached to the schedule (e.g. "Note: ...") separately from the table rows.
- Record which page number(s) each table's content came from.
"""


class ScheduleOfQuantityTable(BaseModel):
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
    def _warn_on_ragged_rows(self) -> "ScheduleOfQuantityTable":
        """Same defensive check as tender_misc_extraction_service.ExtractedTable
        - the LLM occasionally drops or duplicates a cell while re-typing a
        table, silently shifting every later cell in that row into the
        wrong column in the exported Excel. No reliable way to guess which
        cell is missing, so this just makes it loud instead of silent."""
        expected = len(self.columns)
        if not expected:
            return self
        for i, row in enumerate(self.rows, start=1):
            if len(row) != expected:
                logger.warning(
                    "Schedule of Quantity table %r: row %d has %d cell(s) but there are %d column(s) "
                    "(%s) - likely misaligned in the exported Excel. Row content: %r",
                    self.caption or "(untitled)", i, len(row), expected, self.columns, row,
                )
        return self


class ScheduleOfQuantitySection(BaseModel):
    heading: Optional[str] = Field(
        None, description="Exact heading text this table appears under, e.g. 'Schedule of Work'. "
        "Null if the table has no heading of its own."
    )
    source_pages: list[int] = Field(
        default_factory=list, description="Page numbers this table's content was found on."
    )
    tables: list[ScheduleOfQuantityTable] = Field(
        default_factory=list, description="Tables belonging to this section."
    )
    notes: list[str] = Field(
        default_factory=list, description="Footnotes/asterisked notes/caveats attached to this section."
    )


class ScheduleOfQuantityExtraction(BaseModel):
    present: bool = Field(description="True if a genuine Schedule of Quantity table was found.")
    sections: list[ScheduleOfQuantitySection] = Field(
        default_factory=list,
        description="One entry per distinct heading/sub-schedule found. Empty when `present` is False.",
    )


def _build_user_prompt(pages: list[dict]) -> str:
    blocks = []
    for p in pages:
        block = [f"--- Page {p['page_number']} ---", p.get("text", "")]
        tables = p.get("tables") or []
        for i, table in enumerate(tables, start=1):
            if not table:
                continue
            block.append(f"[Page {p['page_number']} parsed table {i}]")
            block.append(json.dumps(table, ensure_ascii=False))
        blocks.append("\n".join(block))

    excerpt = "\n\n".join(blocks)
    return f"OCR text (with parsed tables where available) from {len(pages)} page(s):\n\n{excerpt}"


def _call_llm_structured(
    system_prompt: str,
    user_prompt: str,
    token_callback: Optional[Callable[[int], None]] = None,
) -> ScheduleOfQuantityExtraction:
    logger.info("Using _call_llm_structured (native structured output) for this LLM call.")
    llm = get_llm()
    structured_llm = llm.with_structured_output(ScheduleOfQuantityExtraction)

    with get_openai_callback() as cb:
        response = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        total_tokens = cb.total_tokens
        logger.info("Total Tokens Usage: %d", total_tokens)

    if token_callback:
        token_callback(total_tokens)

    if isinstance(response, ScheduleOfQuantityExtraction):
        return response
    return ScheduleOfQuantityExtraction.model_validate(response)


def _call_llm_fallback(
    system_prompt: str,
    user_prompt: str,
    token_callback: Optional[Callable[[int], None]] = None,
) -> ScheduleOfQuantityExtraction:
    """Fallback path for LLM backends that don't support with_structured_output."""
    logger.info("Using _call_llm_fallback (raw JSON parsing - this LLM backend has no with_structured_output).")
    llm = get_llm()
    schema_hint = (
        "\n\nRespond with ONLY a single JSON object matching exactly this schema "
        "(no markdown fences, no commentary):\n"
        f"{json.dumps(ScheduleOfQuantityExtraction.model_json_schema(), indent=2)}"
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
        return ScheduleOfQuantityExtraction.model_validate_json(raw)
    except Exception as e:
        raise ValueError(f"LLM did not return JSON matching the expected schema: {raw!r}") from e


_QUANTITY_COLUMN_HINT = re.compile(r"qty|quantity", re.IGNORECASE)


def _drop_non_quantity_tables(extraction: ScheduleOfQuantityExtraction) -> ScheduleOfQuantityExtraction:
    """
    Deterministic backstop for the SYSTEM_PROMPT's "must have a Quantity
    column" rule - LLM prompt compliance isn't guaranteed. A real Schedule
    of Quantity always has a Quantity/Qty column, so any table missing one
    (e.g. an unrelated small rate table that slipped into the last few
    pages) gets dropped here before it ever reaches Excel export.
    """
    if not extraction.present:
        return extraction

    kept_sections = []
    for section in extraction.sections:
        kept_tables = [
            table for table in section.tables
            if any(_QUANTITY_COLUMN_HINT.search(col) for col in table.columns)
        ]
        dropped = len(section.tables) - len(kept_tables)
        if dropped:
            logger.warning(
                "Schedule of Quantity: dropped %d table(s) with no Quantity column from section %r "
                "(pages %s) - not a real schedule of quantities.",
                dropped, section.heading, section.source_pages,
            )
        if kept_tables or section.notes:
            kept_sections.append(section.model_copy(update={"tables": kept_tables}))

    return ScheduleOfQuantityExtraction(present=bool(kept_sections), sections=kept_sections)


def extract_data(
    pages: list[dict],
    token_callback: Optional[Callable[[int], None]] = None,
) -> dict:
    """
    Extract Schedule of Quantity from the given OCR pages (the caller is
    expected to have already narrowed `pages` to the last config.SOQ_LAST_PAGES
    pages - see app.pipeline.stages.stage_extract_schedule_of_quantity),
    returning a JSON-ready dict matching the ScheduleOfQuantityExtraction
    schema: {"present": bool, "sections": [ {heading, source_pages, tables, notes}, ... ]}.

    A "present": false result means the LLM genuinely could not find a
    Schedule of Quantity table in the supplied pages - an expected, valid
    result, not an error. Raises ValueError only if the LLM call itself
    fails or its output can't be validated against the schema.
    """
    user_prompt = _build_user_prompt(pages)
    try:
        llm = get_llm()
        if hasattr(llm, "with_structured_output"):
            extraction = _call_llm_structured(SYSTEM_PROMPT, user_prompt, token_callback=token_callback)
        else:
            extraction = _call_llm_fallback(SYSTEM_PROMPT, user_prompt, token_callback=token_callback)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"LLM call failed while extracting schedule of quantity: {e}") from e

    extraction = _drop_non_quantity_tables(extraction)
    if not extraction.present:
        logger.warning("LLM could not find a Schedule of Quantity table in %d page(s).", len(pages))

    return extraction.model_dump(mode="json")


if __name__ == "__main__":
    # Quick manual test with fake OCR pages - hits the real LLM (needs valid
    # AZURE_OPENAI_* env vars, or whatever get_llm() is configured for).
    fake_pages = [
        {
            "page_number": 25,
            "text": "SCHEDULE OF QUANTITIES\n"
            "S.No. Description of Item Unit Quantity Rate Amount",
            "tables": [
                [
                    ["S.No.", "Description of Item", "Unit", "Quantity", "Rate", "Amount"],
                    ["1", "Excavation in ordinary soil", "Cum", "120", "150", "18000"],
                    ["2", "PCC 1:4:8 in foundation", "Cum", "40", "4500", "180000"],
                ]
            ],
        },
    ]

    result = extract_data(fake_pages)
    print(json.dumps(result, indent=2))
