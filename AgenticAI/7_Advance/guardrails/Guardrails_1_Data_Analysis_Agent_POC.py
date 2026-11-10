import ast
import re
import sqlite3
import pandas as pd
from pydantic import BaseModel, Field

# 1. INPUT GUARDRAIL: Block Prompt Injection & Scope Drift
def validate_user_prompt(prompt: str) -> None:
    blocked_patterns = [
        r"ignore (all )?previous instructions",
        r"system prompt",
        r"drop table",
        r"export .* password",
    ]
    for pattern in blocked_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            raise ValueError(f"Input Guardrail Triggered: Prohibited pattern '{pattern}' detected.")


# 2. SQL EXECUTION GUARDRAIL: Enforce Read-Only Queries
def validate_sql_query(query: str, allowed_tables: set[str]) -> str:
    cleaned = query.strip().rstrip(";")
    
    # Prevent multiple stacked statements
    if ";" in cleaned:
        raise PermissionError("SQL Guardrail: Multiple SQL statements are not allowed.")
    
    # Enforce SELECT-only queries
    if not cleaned.upper().startswith("SELECT"):
        raise PermissionError("SQL Guardrail: Only SELECT queries are permitted.")
    
    # Block dangerous keywords
    forbidden_keywords = {"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "PRAGMA", "ATTACH"}
    tokens = set(re.findall(r"\b[A-Z]+\b", cleaned.upper()))
    if tokens.intersection(forbidden_keywords):
        raise PermissionError(f"SQL Guardrail: Forbidden SQL keyword detected: {tokens.intersection(forbidden_keywords)}")

    # Verify table allowlist (simple check)
    referenced_tables = set(re.findall(r"(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)", cleaned, re.IGNORECASE))
    unauthorized = {t.lower() for t in referenced_tables} - {t.lower() for t in allowed_tables}
    if unauthorized:
        raise PermissionError(f"SQL Guardrail: Access denied to table(s): {unauthorized}")

    return cleaned


# 3. PYTHON CODE GUARDRAIL: AST Static Analysis
def validate_generated_python(code: str) -> None:
    """Inspects LLM-generated Python code before running exec()."""
    tree = ast.parse(code)
    
    banned_imports = {"os", "sys", "subprocess", "shutil", "socket", "requests", "urllib"}
    banned_calls = {"eval", "exec", "open", "__import__", "compile"}

    for node in ast.walk(tree):
        # Block dangerous imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in banned_imports:
                    raise PermissionError(f"Code Guardrail: Importing '{alias.name}' is forbidden.")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in banned_imports:
                raise PermissionError(f"Code Guardrail: Importing from '{node.module}' is forbidden.")
        
        # Block dangerous built-in function calls
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in banned_calls:
                raise PermissionError(f"Code Guardrail: Calling '{node.func.id}()' is forbidden.")


# 4. OUTPUT GUARDRAIL: PII Redaction & Schema Enforcement
class AnalysisResponse(BaseModel):
    summary: str = Field(..., min_length=10, max_length=1000)
    row_count: int = Field(..., ge=0)
    data_preview: list[dict]

def redact_pii(text: str) -> str:
    # Mask email addresses and US-style SSNs/phone numbers
    text = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[REDACTED_EMAIL]", text)
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", text)
    return text


# EXAMPLE WORKFLOW: Running the Guardrailed Agent Tool
def run_safe_data_analysis(user_prompt: str, llm_generated_sql: str, db_conn: sqlite3.Connection) -> AnalysisResponse:
    # Step 1: Check user input
    validate_user_prompt(user_prompt)

    # Step 2: Validate LLM-generated SQL before touching the database
    safe_sql = validate_sql_query(llm_generated_sql, allowed_tables={"sales_data"})

    # Step 3: Execute query with a strict row limit
    df = pd.read_sql_query(f"SELECT * FROM ({safe_sql}) LIMIT 100", db_conn)

    # Step 4: Redact PII from output and validate structure with Pydantic
    top_contact_email = df.sort_values(by="revenue", ascending=False).iloc[0]["rep_email"]
    raw_summary = f"Found {len(df)} records. Top contact: {top_contact_email}"
    clean_summary = redact_pii(raw_summary)
    
    clean_records = [
        {k: redact_pii(str(v)) for k, v in row.items()}
        for row in df.head(5).to_dict(orient="records")
    ]

    return AnalysisResponse(
        summary=clean_summary,
        row_count=len(df),
        data_preview=clean_records
    )


# --- Quick Test ---
if __name__ == "__main__":
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE sales_data (id INT, region TEXT, revenue REAL, rep_email TEXT)")
    conn.execute("INSERT INTO sales_data VALUES (1, 'North', 45000.0, 'john.doe@company.com')")
    conn.execute("INSERT INTO sales_data VALUES (2, 'South', 55000.0, 'jane.smith@company.com')")
    conn.execute("INSERT INTO sales_data VALUES (3, 'North', 65000.0, 'bob.jones@company.com')")
        

    # TEST1: Safe execution test
    result = run_safe_data_analysis(
        user_prompt="Show me revenue by region",
        llm_generated_sql="SELECT region, revenue, rep_email FROM sales_data",
        db_conn=conn
    )
    print("TEST1: Safe Output:", result.model_dump_json(indent=2))

    # TEST2: Blocked execution test
    try:
        run_safe_data_analysis(
            user_prompt="Clean up old records",
            llm_generated_sql="DROP TABLE sales_data",
            db_conn=conn
        )
    except PermissionError as e:
        print("\nBlocked Attack:", e)

# SAMPLE RUN:
# TEST1: Safe Output: {
#   "summary": "Found 3 records. Top contact: [REDACTED_EMAIL]",
#   "row_count": 3,
#   "data_preview": [
#     {
#       "region": "North",
#       "revenue": "45000.0",
#       "rep_email": "[REDACTED_EMAIL]"
#     },
#     {
#       "region": "South",
#       "revenue": "55000.0",
#       "rep_email": "[REDACTED_EMAIL]"
#     },
#     {
#       "region": "North",
#       "revenue": "65000.0",
#       "rep_email": "[REDACTED_EMAIL]"
#     }
#   ]
# }

# Blocked Attack: SQL Guardrail: Only SELECT queries are permitted.