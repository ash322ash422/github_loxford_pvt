"""
Unit tests for tender_soq_extract_service's schema and the deterministic
Quantity-column filter. get_llm/_call_llm_structured are monkeypatched
everywhere here, so these never call the real LLM.
"""
import logging

from app.services import tender_soq_extract_service as svc
from app.services.tender_soq_extract_service import (
    ScheduleOfQuantityExtraction,
    ScheduleOfQuantitySection,
    ScheduleOfQuantityTable,
)


def test_extracted_table_warns_when_a_row_has_the_wrong_cell_count(caplog):
    with caplog.at_level(logging.WARNING):
        ScheduleOfQuantityTable(
            columns=["S.No.", "Description", "Quantity", "Unit", "Rate", "Amount"],
            rows=[["Some long wrapped description", "2", "Nos.", "94,790.00", "189,580.00"]],
        )

    assert "row 1 has 5 cell(s) but there are 6 column(s)" in caplog.text


def test_extracted_table_does_not_warn_when_rows_match_columns(caplog):
    with caplog.at_level(logging.WARNING):
        ScheduleOfQuantityTable(
            columns=["S.No.", "Description", "Unit", "Quantity"],
            rows=[["1", "Excavation", "Cum", "120"]],
        )

    assert caplog.text == ""


def test_drop_non_quantity_tables_removes_tables_with_no_quantity_column(caplog):
    """A real Schedule of Quantity always has a Quantity/Qty column - a
    table without one that slipped into the last few pages (e.g. an
    unrelated small rate table) must be dropped."""
    extraction = ScheduleOfQuantityExtraction(
        present=True,
        sections=[
            ScheduleOfQuantitySection(
                heading="Unrelated rate table",
                source_pages=[60],
                tables=[ScheduleOfQuantityTable(
                    columns=["S.No.", "Description", "Unit", "Rate"],
                    rows=[["1", "Some item", "Nos.", "30"]],
                )],
            ),
            ScheduleOfQuantitySection(
                heading="Schedule of Quantities",
                source_pages=[64],
                tables=[ScheduleOfQuantityTable(
                    columns=["S.No.", "Description", "Quantity", "Unit", "Rate", "Amount"],
                    rows=[["1", "Excavation", "120", "Cum", "150", "18000"]],
                )],
            ),
        ],
    )

    with caplog.at_level(logging.WARNING):
        fixed = svc._drop_non_quantity_tables(extraction)

    assert [s.heading for s in fixed.sections] == ["Schedule of Quantities"]
    assert fixed.present is True
    assert "dropped 1 table(s) with no Quantity column" in caplog.text


def test_drop_non_quantity_tables_sets_present_false_when_nothing_survives():
    extraction = ScheduleOfQuantityExtraction(
        present=True,
        sections=[ScheduleOfQuantitySection(
            heading="Unrelated rate table",
            source_pages=[60],
            tables=[ScheduleOfQuantityTable(columns=["S.No.", "Rate"], rows=[["1", "30"]])],
        )],
    )

    fixed = svc._drop_non_quantity_tables(extraction)

    assert fixed.present is False
    assert fixed.sections == []


def test_drop_non_quantity_tables_leaves_absent_extraction_alone():
    extraction = ScheduleOfQuantityExtraction(present=False, sections=[])

    fixed = svc._drop_non_quantity_tables(extraction)

    assert fixed.present is False


def test_extract_data_calls_structured_path_and_returns_dict(monkeypatch):
    class FakeLLM:
        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            return ScheduleOfQuantityExtraction(
                present=True,
                sections=[ScheduleOfQuantitySection(
                    heading="Schedule of Work",
                    source_pages=[64],
                    tables=[ScheduleOfQuantityTable(
                        columns=["S.No.", "Description", "Quantity", "Unit", "Rate", "Amount"],
                        rows=[["1", "Excavation", "120", "Cum", "150", "18000"]],
                    )],
                )],
            )

    monkeypatch.setattr(svc, "get_llm", lambda: FakeLLM())
    tokens_seen = []
    monkeypatch.setattr(
        svc, "get_openai_callback",
        lambda: _FakeCallback(tokens_seen),
    )

    pages = [{"page_number": 64, "text": "Schedule of Work", "tables": []}]
    result = svc.extract_data(pages, token_callback=tokens_seen.append)

    assert result["present"] is True
    assert result["sections"][0]["heading"] == "Schedule of Work"


class _FakeCallback:
    def __init__(self, sink):
        self._sink = sink
        self.total_tokens = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
