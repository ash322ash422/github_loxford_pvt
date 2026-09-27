"""
Defines what fields we ask the LLM to extract, and builds the prompt.

To extract a new field: add one entry to FIELDS_TO_EXTRACT. If it's a
date or an amount, also add its name to DATE_FIELDS / AMOUNT_FIELDS in
app/services/validation.py so it gets normalized automatically.
"""
import json

FIELDS_TO_EXTRACT = [
    # {"name": "nit_number", "description": "This is the NIT number."},
    # {"name": "name_of_work_location", "description": "Name / Type of the work and location."},
    # {"name": "estimated_cost", "description": "Estimated cost put to the tender."},
    # {"name": "earnest_money", "description": "Earnest Money Deposit or EMD amount."},
    # {"name": "completion_period", "description": "Period of Completion of the work."},
    # {"name": "submission_deadline", "description": "Last date and time for bid submission."},
    # {"name": "bid_opening_date", "description": "Date and time of bid opening."},

    {"name": "NIT Number", "description": "This is the NIT number."},
    {"name": "Name Of Work Location", "description": "Name / Type of the work and location."},
    {"name": "Estimated Cost", "description": "Estimated cost put to the tender."},
    {"name": "Earnest Money", "description": "Earnest Money Deposit or EMD amount."},
    {"name": "Completion Period", "description": "Period of Completion of the work."},
    {"name": "Submission Deadline", "description": "Last date and time for bid submission."},
    {"name": "Bid Opening Date", "description": "Date and time of bid opening."},


]


def build_field_schema(fields: list) -> str:
    return json.dumps({f["name"]: "" for f in fields}, indent=4)


def format_page_for_llm(page: dict) -> str:
    return f"""
        ====================================================
        PAGE {page["page_number"]}
        ====================================================

        TEXT
        -----

        {page["text"]}


        KEY VALUE PAIRS
        ---------------

        {json.dumps(page["key_value_pairs"], indent=4, ensure_ascii=False)}


        TABLES
        ------

        {json.dumps(page["tables"], indent=4, ensure_ascii=False)}

    """


def format_pages_for_llm(pages: list) -> str:
    return "\n".join(format_page_for_llm(p) for p in pages)


def build_extraction_prompt(pages: list, fields: list) -> str:
    field_descriptions = "\n".join(f"- {f['name']}: {f['description']}" for f in fields)
    schema = build_field_schema(fields)
    document = format_pages_for_llm(pages)

    return f"""
        You are an expert in analysing Government Tender documents.

        Your task is to extract ONLY the requested fields.

        Use the following priority while searching:

        1. Key Value Pairs
        2. Tables
        3. Text

        Rules

        - Never guess.
        - If a value is missing, return an empty string.
        - Return ONLY valid JSON.
        - Do not explain anything.
        - Do not return Markdown.
        - Do not return code blocks.
        - If the same field appears multiple times, choose the most complete value.

        --------------------------------------------------

        FIELDS TO EXTRACT

        {field_descriptions}

        --------------------------------------------------

        Return EXACTLY this JSON structure

        {schema}

        --------------------------------------------------

        DOCUMENT

        {document}

    """
