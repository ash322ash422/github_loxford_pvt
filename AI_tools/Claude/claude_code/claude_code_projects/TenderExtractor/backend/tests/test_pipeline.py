"""
Unit tests for the parts of the pipeline that don't require live Azure
credentials: prompt building, LLM-result merging, and field validation.

Run with:
    pytest tests/
"""
from app.services.tender_nit_extract_service import merge_results
from app.services.prompt import FIELDS_TO_EXTRACT, build_extraction_prompt
from app.services.validation import validate_amount, validate_date, validate_nit_extracted_json


def test_merge_results_first_non_empty_wins():
    partials = [
        {"NIT Number": "", "Earnest Money": "Rs. 50,000"},
        {"NIT Number": "NIT/2026/12", "Earnest Money": "Rs. 999"},
    ]
    merged = merge_results(partials)
    assert merged["NIT Number"] == "NIT/2026/12"
    assert merged["Earnest Money"] == "Rs. 50,000"


def test_validate_amount_normalizes_currency_formatting():
    result = validate_amount("Rs. 5,29,995/-")
    assert result["valid"] is True
    assert result["normalized"] == 529995.0
    assert result["original"] == "Rs. 5,29,995/-"


def test_validate_amount_handles_missing_value():
    result = validate_amount("")
    assert result["valid"] is False
    assert result["normalized"] is None


def test_validate_date_parses_ddmmyyyy_inside_free_text():
    result = validate_date("17:00 hrs. on 17.07.2026")
    assert result["valid"] is True
    assert result["normalized"] == "2026-07-17"


def test_validate_date_rejects_unparseable_text():
    result = validate_date("sometime next month")
    assert result["valid"] is False
    assert result["normalized"] is None


def test_validate_nit_extracted_json_normalizes_date_and_amount_fields():
    validated = validate_nit_extracted_json(
        {
            "Submission Deadline": "17:00 hrs. on 17.07.2026",
            "Estimated Cost": "Rs. 5,29,995/-",
        }
    )
    assert validated["Submission Deadline"]["valid"] is True
    assert validated["Submission Deadline"]["normalized"] == "2026-07-17"
    assert validated["Estimated Cost"]["valid"] is True
    assert validated["Estimated Cost"]["normalized"] == 529995.0


def test_validate_nit_extracted_json_preserves_originals_for_non_typed_fields():
    validated = validate_nit_extracted_json({"NIT Number": "NIT/2026/12"})
    assert validated["NIT Number"]["original"] == "NIT/2026/12"
    assert "normalized" not in validated["NIT Number"]


def test_build_extraction_prompt_includes_all_field_names():
    pages = [{"page_number": 1, "text": "sample", "tables": [], "key_value_pairs": []}]
    prompt = build_extraction_prompt(pages, FIELDS_TO_EXTRACT)
    for field in FIELDS_TO_EXTRACT:
        assert field["name"] in prompt
