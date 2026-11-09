"""
Homework Fact-Checker Bot
==========================
Brain   : an OpenAI chat model (gpt-4o-mini by default, swap for gpt-4o)
Tool 1  : wikipedia_search        -> verifies dates, names, historical facts
Tool 2  : save_fact_check_report  -> appends a report to the assignment file

Usage:
    python app.py                          # uses sample_assignment.txt
    python app.py my_essay.txt             # any .txt file
    python app.py my_essay.pdf             # any .pdf file (uses pypdf)
"""

import os
import sys

from langchain.agents import create_agent
from pypdf import PdfReader

from tools import wikipedia_search, save_fact_check_report


from dotenv import load_dotenv
load_dotenv() 


MODEL_NAME = "gpt-4o-mini"  # try "gpt-4o" for higher-quality fact checking

SYSTEM_PROMPT = """You are a careful, encouraging fact-checking assistant for students.
You will be given a student's written paragraph. Do the following:

1. Read the paragraph and pull out every checkable factual claim
   (dates, names, places, events, statistics).
2. For EACH claim, call the `wikipedia_search` tool to verify it.
   Never rely on memory alone -- always search.
3. Decide whether each claim is Correct, Incorrect, or Unverifiable.
   If it's incorrect, state the correct fact.
4. Write a short Markdown report with one bullet per claim, using
   ✅ Correct / ❌ Incorrect / ⚠️ Unverifiable, plus a one-line explanation.
   Keep the tone friendly and constructive -- this is for a student, not a
   gotcha exercise.
5. Once every claim has been checked, call `save_fact_check_report` EXACTLY
   ONCE with the finished Markdown report, using file_path="{file_path}".
"""


def load_assignment(path: str) -> str:
    """Read a student assignment from either a .txt or .pdf file."""
    if path.lower().endswith(".pdf"):
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit(
            "Please set your OPENAI_API_KEY environment variable first, e.g.\n"
            "  export OPENAI_API_KEY=sk-...\n"
        )

    assignment_path = sys.argv[1] if len(sys.argv) > 1 else "sample_assignment.txt"
    essay_text = load_assignment(assignment_path)

    agent = create_agent(
        model=MODEL_NAME,
        tools=[wikipedia_search, save_fact_check_report],
        system_prompt=SYSTEM_PROMPT.format(file_path=assignment_path),
    )

    print(f"Fact-checking '{assignment_path}' ...\n(this calls the LLM + Wikipedia)\n")

    result = agent.invoke(
        {"messages": [{"role": "user", "content": f"Here is the paragraph:\n\n{essay_text}"}]}
    )

    final_message = result["messages"][-1]
    print("=== Agent's final message ===")
    print(final_message.content)
    print(f"\nDone! Open '{assignment_path}' to see the appended Fact-Check Report.")


if __name__ == "__main__":
    main()
