"""
Normalizes raw LLM output into typed values and flags whether each
field parsed cleanly, without discarding the original text.

To validate a new field type: write a `validate_x(value) -> dict`
function following the same {"original", "normalized", "valid"} shape,
then add the field name to the matching list below.
"""
import re
from datetime import datetime

DATE_FIELDS = ["Submission Deadline", "Bid Opening Date"]
AMOUNT_FIELDS = ["Estimated Cost", "Earnest Money"]


def validate_amount(value: str) -> dict:
    result = {"original": value, "normalized": None, "valid": False}

    if not value:
        return result

    cleaned = (
        value.replace("Rs.", "")
        .replace("Rs", "")
        .replace("₹", "")
        .replace(",", "")
        .replace("/-", "")
        .strip()
    )

    try:
        result["normalized"] = float(cleaned)
        result["valid"] = True
    except ValueError:
        pass

    return result


def validate_date(value: str) -> dict:
    """Handles dates like '17.07.2026' or '17:00 hrs. on 17.07.2026'."""
    result = {"original": value, "normalized": None, "valid": False}

    if not value:
        return result

    match = re.search(r"\d{2}\.\d{2}\.\d{4}", value)
    if not match:
        return result

    try:
        dt = datetime.strptime(match.group(), "%d.%m.%Y")
        result["normalized"] = dt.strftime("%Y-%m-%d")
        result["valid"] = True
    except ValueError:
        pass

    return result


def validate_nit_extracted_json(data: dict) -> dict:
    """Original values are always preserved alongside the normalized ones."""
    validated = {}

    for field, value in data.items():
        if field in DATE_FIELDS:
            validated[field] = validate_date(value)
        elif field in AMOUNT_FIELDS:
            validated[field] = validate_amount(value)
        else:
            validated[field] = {"original": value}

    return validated
