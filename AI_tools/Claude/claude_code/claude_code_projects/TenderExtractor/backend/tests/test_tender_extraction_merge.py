"""
Unit tests for tender_extraction_service's page-chunking and cross-batch
merge logic. _extract_chunk is monkeypatched everywhere here, so these
never call the real LLM - they test the pure logic: how pages get split
into batches, and how per-batch results get stitched back together
(re-merging sections whose heading repeats across batches, per
_merge_extractions' docstring).
"""
import logging

from app.services import tender_misc_extraction_service as svc
from app.services.tender_misc_extraction_service import (
    ExtractedField,
    ExtractedItem,
    ExtractedSection,
    ExtractedTable,
    TenderExtraction,
    _merge_extractions,
    _normalize_heading,
)


def _extraction(**fields) -> TenderExtraction:
    """Build a TenderExtraction with the three required fields, defaulting
    any not passed in to present=False/no sections."""
    defaults = {
        "terms_and_conditions": ExtractedField(present=False),
        "acceptable_make": ExtractedField(present=False),
        "documents_to_be_scanned_and_uploaded": ExtractedField(present=False),
    }
    defaults.update(fields)
    return TenderExtraction(**defaults)


def test_normalize_heading_collapses_whitespace_and_case():
    assert _normalize_heading("  General   Terms &  Conditions ") == "general terms & conditions"
    assert _normalize_heading("General Terms & Conditions") == "general terms & conditions"


def test_normalize_heading_returns_none_for_none():
    assert _normalize_heading(None) is None


def test_merge_extractions_combines_matching_headings_across_chunks():
    chunk1 = _extraction(
        terms_and_conditions=ExtractedField(
            present=True,
            sections=[
                ExtractedSection(
                    heading="General Terms & Conditions",
                    source_pages=[6],
                    items=[ExtractedItem(number="1", text="First clause.")],
                )
            ],
        )
    )
    chunk2 = _extraction(
        terms_and_conditions=ExtractedField(
            present=True,
            sections=[
                ExtractedSection(
                    heading="  General   Terms &  Conditions ",  # same heading, different whitespace/case
                    source_pages=[7],
                    items=[ExtractedItem(number="2", text="Second clause.")],
                )
            ],
        )
    )

    merged = _merge_extractions([chunk1, chunk2])

    assert merged.terms_and_conditions.present is True
    assert len(merged.terms_and_conditions.sections) == 1
    section = merged.terms_and_conditions.sections[0]
    assert section.heading == "General Terms & Conditions"  # first-seen heading text wins
    assert section.source_pages == [6, 7]
    assert [item.text for item in section.items] == ["First clause.", "Second clause."]


def test_merge_extractions_keeps_distinct_headings_as_separate_sections():
    chunk1 = _extraction(
        terms_and_conditions=ExtractedField(
            present=True,
            sections=[ExtractedSection(heading="Terms & Conditions", source_pages=[6])],
        )
    )
    chunk2 = _extraction(
        terms_and_conditions=ExtractedField(
            present=True,
            sections=[ExtractedSection(heading="General Conditions", source_pages=[9])],
        )
    )

    merged = _merge_extractions([chunk1, chunk2])

    headings = {s.heading for s in merged.terms_and_conditions.sections}
    assert headings == {"Terms & Conditions", "General Conditions"}


def test_merge_extractions_never_merges_unheaded_sections_together():
    chunk1 = _extraction(
        acceptable_make=ExtractedField(
            present=True,
            sections=[ExtractedSection(heading=None, source_pages=[3], items=[ExtractedItem(text="MS Pipe: Jindal")])],
        )
    )
    chunk2 = _extraction(
        acceptable_make=ExtractedField(
            present=True,
            sections=[ExtractedSection(heading=None, source_pages=[8], items=[ExtractedItem(text="Cable: Havells")])],
        )
    )

    merged = _merge_extractions([chunk1, chunk2])

    assert len(merged.acceptable_make.sections) == 2
    assert all(s.heading is None for s in merged.acceptable_make.sections)


def test_merge_extractions_concatenates_tables_across_chunks_for_same_heading():
    """A table embedded in a section can be split across pages/batches -
    confirm a table split across chunks under the same heading gets
    concatenated (both ExtractedTable blocks kept, not dropped)."""
    chunk1 = _extraction(
        terms_and_conditions=ExtractedField(
            present=True,
            sections=[
                ExtractedSection(
                    heading="General Terms & Conditions",
                    source_pages=[20],
                    tables=[ExtractedTable(
                        columns=["S.No.", "Description", "Unit", "Rate"],
                        rows=[["1", "Excavation", "Cum", "120"]],
                    )],
                )
            ],
        )
    )
    chunk2 = _extraction(
        terms_and_conditions=ExtractedField(
            present=True,
            sections=[
                ExtractedSection(
                    heading="General Terms & Conditions",
                    source_pages=[21],
                    tables=[ExtractedTable(
                        columns=["S.No.", "Description", "Unit", "Rate"],
                        rows=[["2", "PCC 1:4:8", "Cum", "40"]],
                    )],
                )
            ],
        )
    )

    merged = _merge_extractions([chunk1, chunk2])

    assert merged.terms_and_conditions.present is True
    assert len(merged.terms_and_conditions.sections) == 1
    section = merged.terms_and_conditions.sections[0]
    assert section.source_pages == [20, 21]
    assert len(section.tables) == 2
    assert section.tables[0].rows == [["1", "Excavation", "Cum", "120"]]
    assert section.tables[1].rows == [["2", "PCC 1:4:8", "Cum", "40"]]


def test_merge_extractions_present_true_if_any_chunk_found_it():
    chunk1 = _extraction(acceptable_make=ExtractedField(present=False, sections=[]))
    chunk2 = _extraction(
        acceptable_make=ExtractedField(present=True, sections=[ExtractedSection(heading="Approved Makes")])
    )

    merged = _merge_extractions([chunk1, chunk2])

    assert merged.acceptable_make.present is True


def test_extract_data_splits_pages_into_batches_of_requested_size(monkeypatch):
    calls = []

    def fake_extract_chunk(batch, max_pages, token_callback):
        calls.append([p["page_number"] for p in batch])
        if token_callback:
            token_callback(100)
        return _extraction()

    monkeypatch.setattr(svc, "_extract_chunk", fake_extract_chunk)

    pages = [{"page_number": n, "text": f"page {n}"} for n in range(1, 6)]  # 5 pages
    tokens_seen = []

    result = svc.extract_data(pages, page_chunk_size=2, token_callback=tokens_seen.append)

    assert calls == [[1, 2], [3, 4], [5]]  # 3 batches of up to 2 pages each
    assert tokens_seen == [100, 100, 100]
    assert result["terms_and_conditions"]["present"] is False


def test_extract_data_without_page_chunk_size_sends_everything_in_one_call(monkeypatch):
    calls = []

    def fake_extract_chunk(batch, max_pages, token_callback):
        calls.append([p["page_number"] for p in batch])
        return _extraction()

    monkeypatch.setattr(svc, "_extract_chunk", fake_extract_chunk)

    pages = [{"page_number": n, "text": f"page {n}"} for n in range(1, 6)]
    svc.extract_data(pages)

    assert calls == [[1, 2, 3, 4, 5]]


def test_extracted_table_warns_when_a_row_has_the_wrong_cell_count(caplog):
    """Regression test for a real bug: the LLM dropped a row's S.No. cell
    while re-typing a table, silently shifting every later cell in that
    row one column left in the exported Excel. There's no reliable way to
    auto-correct a dropped cell, so this just needs to turn it into a
    loud, traceable warning instead of a silent corruption."""
    with caplog.at_level(logging.WARNING):
        ExtractedTable(
            caption=None,
            columns=["S.No.", "Description", "Quantity", "Unit", "Rate", "Amount"],
            rows=[["Some long wrapped description", "2", "Nos.", "94,790.00", "189,580.00"]],
        )

    assert "row 1 has 5 cell(s) but there are 6 column(s)" in caplog.text


def test_extracted_table_does_not_warn_when_rows_match_columns(caplog):
    with caplog.at_level(logging.WARNING):
        ExtractedTable(
            caption="Approved Makes",
            columns=["S.No.", "Description", "Unit", "Rate"],
            rows=[["1", "2x1.5 sq.mm fire alarm armored cable", "P/Mtrs", "30"]],
        )

    assert caplog.text == ""


def test_attach_missing_terms_tables_pulls_table_from_raw_ocr_when_llm_omitted_it(caplog):
    """Regression test for a real bug: the LLM correctly filed a Terms and
    Conditions section under terms_and_conditions but simply didn't
    extract the small table that's actually on that page. Document
    Intelligence's own raw parse (already proven correct) should be used
    to fill it in rather than leaving the table missing."""
    extraction = _extraction(
        terms_and_conditions=ExtractedField(
            present=True,
            sections=[ExtractedSection(heading="TERMS AND CONDITIONS", source_pages=[30], items=[
                ExtractedItem(number="1", text="Materials shall be got approved..."),
            ])],
        )
    )
    pages = [
        {"page_number": 30, "text": "...", "tables": [
            [
                ["S.No.", "Description of Items", "Unit", "Rate"],
                ["1", "2x1.5 sq.mm fire alarm armored cable", "P/Mtrs", "30"],
                ["2", "Addressable photo thermal detector", "Each", "90"],
            ]
        ]},
    ]

    with caplog.at_level(logging.WARNING):
        fixed = svc._attach_missing_terms_tables_from_raw_ocr(extraction, pages)

    section = fixed.terms_and_conditions.sections[0]
    assert len(section.tables) == 1
    assert section.tables[0].columns == ["S.No.", "Description of Items", "Unit", "Rate"]
    assert len(section.tables[0].rows) == 2
    assert "attached a table from page 30" in caplog.text


def test_attach_missing_terms_tables_skips_sections_that_already_have_a_table():
    extraction = _extraction(
        terms_and_conditions=ExtractedField(
            present=True,
            sections=[ExtractedSection(
                heading="TERMS AND CONDITIONS", source_pages=[30],
                tables=[ExtractedTable(columns=["A"], rows=[["existing"]])],
            )],
        )
    )
    pages = [{"page_number": 30, "text": "...", "tables": [[["X"], ["unrelated"]]]}]

    fixed = svc._attach_missing_terms_tables_from_raw_ocr(extraction, pages)

    assert len(fixed.terms_and_conditions.sections[0].tables) == 1
    assert fixed.terms_and_conditions.sections[0].tables[0].columns == ["A"]


def test_attach_missing_terms_tables_does_not_reclaim_a_table_used_elsewhere():
    extraction = _extraction(
        terms_and_conditions=ExtractedField(
            present=True,
            sections=[ExtractedSection(heading="TERMS AND CONDITIONS", source_pages=[30])],
        ),
        acceptable_make=ExtractedField(
            present=True,
            sections=[ExtractedSection(heading="Approved Makes", source_pages=[30], tables=[
                ExtractedTable(columns=["S.No.", "Rate"], rows=[["1", "30"]]),
            ])],
        ),
    )
    pages = [{"page_number": 30, "text": "...", "tables": [[["S.No.", "Rate"], ["1", "30"]]]}]

    fixed = svc._attach_missing_terms_tables_from_raw_ocr(extraction, pages)

    assert fixed.terms_and_conditions.sections[0].tables == []


def test_drop_non_terms_tables_removes_signature_scope_and_inventory_tables(caplog):
    """Regression test for a real bug: three unrelated things got swept
    into Terms and Conditions from the same broader "Maintenance of
    Fire-Fighting System" heading - a two-column signature block, a
    scope-of-work table, and an equipment inventory table. None are terms
    or conditions; the section's genuine clause item must survive."""
    extraction = _extraction(
        terms_and_conditions=ExtractedField(
            present=True,
            sections=[
                ExtractedSection(
                    heading="Maintenance of Fire-Fighting System",
                    source_pages=[61, 62, 63, 64],
                    items=[ExtractedItem(number="1", text="A genuine procedural clause.")],
                    tables=[
                        ExtractedTable(
                            columns=["Assistant Engineer (E) (P)", "Executive Engineer (E)"],
                            rows=[["President Estate Elect. Division", "President Estate Elect. Division"]],
                        ),
                        ExtractedTable(
                            columns=["S. No.", "Work Involved"],
                            rows=[["1", "Siamese connections operational testing..."]],
                        ),
                        ExtractedTable(
                            columns=["S.No.", "Item", "Pump Room", "Terrace", "Total", "Unit"],
                            rows=[["1", "Wet Riser main Pump (75 HP)", "1", "0", "1", "No."]],
                        ),
                    ],
                ),
            ],
        )
    )

    with caplog.at_level(logging.WARNING):
        fixed = svc._drop_non_terms_tables_from_terms_and_conditions(extraction)

    section = fixed.terms_and_conditions.sections[0]
    assert section.tables == []
    assert [item.text for item in section.items] == ["A genuine procedural clause."]
    assert "a signature block" in caplog.text
    assert "a scope-of-work/job-description table" in caplog.text
    assert "an equipment inventory table" in caplog.text


def test_drop_non_terms_tables_leaves_genuine_tables_alone():
    extraction = _extraction(
        terms_and_conditions=ExtractedField(
            present=True,
            sections=[ExtractedSection(
                heading="SECTION-II GENERAL CONDITIONS",
                source_pages=[20],
                tables=[ExtractedTable(
                    columns=["Sl.No.", "Description of E&M works", "Estimated cost in lacs"],
                    rows=[["1", "Fire alarm system", "5"]],
                )],
            )],
        )
    )

    fixed = svc._drop_non_terms_tables_from_terms_and_conditions(extraction)

    assert len(fixed.terms_and_conditions.sections[0].tables) == 1
