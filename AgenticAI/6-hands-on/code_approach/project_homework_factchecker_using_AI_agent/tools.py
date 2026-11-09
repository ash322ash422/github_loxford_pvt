"""
tools.py
--------
The two "hands" of our agent, as described in the project brief:

  Tool 1 (Search)  -> wikipedia_search        : verifies facts on Wikipedia
  Tool 2 (Action)  -> save_fact_check_report  : appends the report to the file
                                                 (stand-in for a "Google Docs
                                                 append" node — see README)
"""

from langchain.tools import tool
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper


# ---------------------------------------------------------------------------
# TOOL 1 (Search): look facts up on Wikipedia
# ---------------------------------------------------------------------------
# WikipediaAPIWrapper needs no API key, which keeps the demo classroom-friendly.
# top_k_results / doc_content_chars_max keep each lookup short so the LLM
# doesn't get flooded with text.
wikipedia_search = WikipediaQueryRun(
    api_wrapper=WikipediaAPIWrapper(top_k_results=2, doc_content_chars_max=1500)
)
wikipedia_search.name = "wikipedia_search"
wikipedia_search.description = (
    "Look up a fact, date, name, or event on Wikipedia to check whether a "
    "claim is true. Input should be a short search phrase, e.g. "
    "'French Revolution start year' or 'Napoleon Bonaparte coronation'."
)


# ---------------------------------------------------------------------------
# TOOL 2 (Action): append the finished report to the assignment file
# ---------------------------------------------------------------------------
@tool
def save_fact_check_report(report_markdown: str, file_path: str = "sample_assignment.txt") -> str:
    """
    Append a completed Fact-Check Report to the bottom of the student's
    assignment file. Call this exactly ONCE, after you have finished
    checking every claim.

    Args:
        report_markdown: The full report text, already written in Markdown.
        file_path: Path to the student's assignment file to append to.
    """
    with open(file_path, "a", encoding="utf-8") as f:
        f.write("\n\n---\n## 🔍 Fact-Check Report\n")
        f.write(report_markdown.strip())
        f.write("\n")
    return f"Report successfully appended to {file_path}"
