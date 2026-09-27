BANNED_KEYWORDS = [
    "city",
    "address",
    "location",
    "where does customer live",
    "residence",
    "resident"
]

BANNED_SQL_PATTERNS = [
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate"
]

def is_safe_question(question):

    question = question.lower()

    for keyword in BANNED_KEYWORDS:

        if keyword in question:
            return False

    return True


def is_safe_sql(sql_query):

    sql_query = sql_query.lower()

    if not sql_query.startswith("select"):
        return False

    for keyword in BANNED_SQL_PATTERNS:

        if keyword in sql_query:
            return False

    # Prevent exposing city column
    if "city" in sql_query:
        return False

    return True