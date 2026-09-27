"""
Smart Procurement Auditing - LLM Investigator Agent (LangChain/LangGraph edition)
====================================================================================
Same role as llm_investigator_agent.py (the raw-OpenAI-SDK version): takes ONE
transaction the rule engine (ai_procurement_audit_agent.py) already flagged, and
INVESTIGATES it - deciding for itself which tools to call, in which order, before
writing a structured judgment. This version is rebuilt on your installed stack:

    langchain            - create_agent(): the agent loop (model + tools + prompt)
    langchain-openai      - ChatOpenAI: the model, still backed by the OpenAI API
    langgraph             - the graph runtime create_agent() compiles to under the
                             hood; also what powers agent.stream() for live narration
    pydantic              - response_format schema for the final structured judgment

Tested against: langchain 1.3.x, langchain-openai 1.5.x, langgraph 1.2.x
(the same generation as the versions you're running).

Setup
-----
    pip install langchain langchain-openai langgraph pydantic --break-system-packages
    export OPENAI_API_KEY="sk-..."
    export OPENAI_MODEL="gpt-4o-mini"   # optional, this is the default

Run
---
    python3 langchain_investigator_agent.py EXP-1015

Facilitator note: same story as the raw-SDK version - run this right after the
rule-engine demo on a transaction it flagged. EXP-1015 (the shell-vendor case)
tells the best live story. The printed [Agent calls ...] / [Tool result] lines
come from streaming the LangGraph state, so the room watches the tool-call loop
happen in real time, not a canned transcript.
"""

import csv
import json
import os
import sys
from typing import List, Literal

from dotenv import load_dotenv

# Load the environment variables from the .env file
load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
EXPENSES_CSV = os.path.join(DATA_DIR, "expenses_demo.csv")
VENDOR_REGISTRY_JSON = os.path.join(DATA_DIR, "vendor_registry.json")
MODEL_NAME = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


# ----------------------------------------------------------------------
# Data access layer - unchanged from the raw-SDK version. In a real
# deployment these would hit the ERP, vendor master, and approval-
# workflow APIs instead of a CSV and a JSON file.
# ----------------------------------------------------------------------

def load_transactions():
    with open(EXPENSES_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_vendor_registry():
    with open(VENDOR_REGISTRY_JSON, encoding="utf-8") as f:
        return json.load(f)


TRANSACTIONS = load_transactions()
TRANSACTIONS_BY_ID = {t["expense_id"]: t for t in TRANSACTIONS}
VENDOR_REGISTRY = load_vendor_registry()


# ----------------------------------------------------------------------
# Tools. `@tool` reads the function's type hints and docstring to build
# the JSON schema the model sees - no hand-written tool schema needed,
# unlike the raw-SDK version where TOOL_SCHEMAS had to be written by hand.
# ----------------------------------------------------------------------

try:
    from langchain.tools import tool
except ImportError:                              # fallback for older layouts
    from langchain_core.tools import tool


@tool
def get_transaction(expense_id: str) -> str:
    """Fetch the full record for one expense/procurement transaction by its ID (e.g. EXP-1015)."""
    t = TRANSACTIONS_BY_ID.get(expense_id)
    if not t:
        return json.dumps({"error": f"No transaction found with id {expense_id}"})
    return json.dumps(t)


@tool
def list_transactions_by_vendor(vendor: str) -> str:
    """List every transaction billed by a given vendor, across all employees.
    Use this to check whether one vendor is being billed by multiple different people."""
    matches = [t for t in TRANSACTIONS if t["vendor"].lower() == vendor.lower()]
    return json.dumps({"vendor": vendor, "count": len(matches), "transactions": matches})


@tool
def list_transactions_by_employee(employee: str) -> str:
    """List every transaction filed by a given employee.
    Use this to check for patterns like repeated near-threshold amounts or repeated vendor use."""
    matches = [t for t in TRANSACTIONS if t["employee"].lower() == employee.lower()]
    return json.dumps({"employee": employee, "count": len(matches), "transactions": matches})


@tool
def get_vendor_registry_info(vendor: str) -> str:
    """Look up a vendor's master-record data: registration date, GST/tax status, registered
    address, bank verification, how many distinct employees have paid it, and any prior internal
    fraud flags. This is the single most important tool for judging shell-vendor risk."""
    entry = VENDOR_REGISTRY.get(vendor)
    if not entry:
        return json.dumps({
            "vendor": vendor, "found": False,
            "note": "Vendor not found in registry - not yet onboarded, or a name mismatch worth checking.",
        })
    return json.dumps({"vendor": vendor, "found": True, **entry})


@tool
def get_approval_pattern(employee: str) -> str:
    """Check an employee's approval history: how many of their own transactions they approved
    themselves, and which approvers they normally use. Use this to assess segregation-of-duties risk."""
    emp_txns = [t for t in TRANSACTIONS if t["employee"].lower() == employee.lower()]
    if not emp_txns:
        return json.dumps({"employee": employee, "error": "No transaction history for this employee"})
    self_approved = [t for t in emp_txns if t["employee"] == t["approver"]]
    approvers = sorted({t["approver"] for t in emp_txns})
    return json.dumps({
        "employee": employee,
        "total_transactions": len(emp_txns),
        "self_approved_count": len(self_approved),
        "self_approved_ids": [t["expense_id"] for t in self_approved],
        "distinct_approvers_used": approvers,
    })


TOOLS = [
    get_transaction,
    list_transactions_by_vendor,
    list_transactions_by_employee,
    get_vendor_registry_info,
    get_approval_pattern,
]


# ----------------------------------------------------------------------
# Structured final judgment. In the raw-SDK version this was a hand-
# rolled "submit_judgment" tool. Here it's a Pydantic model passed as
# response_format=; create_agent runs the normal tool loop and then
# fills this schema as the last step, returned in result["structured_response"].
# ----------------------------------------------------------------------

from pydantic import BaseModel, Field


class InvestigationJudgment(BaseModel):
    """Final investigation judgment for a flagged procurement/expense transaction."""

    risk_level: Literal["Low", "Medium", "High"] = Field(description="Overall risk assessment.")
    headline: str = Field(description="One sentence summarizing the finding.")
    evidence: List[str] = Field(
        max_length=5,
        description="2-5 specific, cited facts gathered from the tools that support the "
                     "judgment - not general statements.",
    )
    recommended_action: str = Field(description="What the audit team should do next, in one sentence.")
    confidence: Literal["Low", "Medium", "High"] = Field(description="Confidence in this judgment.")


SYSTEM_PROMPT = """You are a procurement fraud investigator agent for a corporate audit team.

You have just been handed ONE transaction that a rule-based triage system already flagged
for one or more of these policy concerns: missing receipts, threshold shaving, self-approval,
spend structuring, shared/shell-vendor patterns, or control bypass (personal card use).

Your job is NOT to re-run those checks. Your job is to INVESTIGATE like a human auditor would:
pull the transaction, then decide for yourself what else you need to know before you can form
a defensible judgment - the vendor's registry profile, whether the same vendor bills other
employees, whether the filer has a pattern of self-approval, whether related transactions exist.

Call tools as needed, in whatever order makes sense given what you learn. Do not call a tool
that clearly won't add new information. Every item in your final evidence list must be a
specific fact you actually pulled via a tool call (cite the vendor registry field, the
approval count, the related transaction ID, etc.) - not a restatement of the original flag."""


# ----------------------------------------------------------------------
# Agent construction and the live-narrated run.
# ----------------------------------------------------------------------

def build_agent(model=None):
    from langchain.agents import create_agent
    from langchain.agents.structured_output import ToolStrategy

    if model is None:
        from langchain_openai import ChatOpenAI
        api_key =OPENAI_API_KEY
        if not api_key:
            sys.exit('OPENAI_API_KEY is not set. Run: export OPENAI_API_KEY="sk-..."')
        # max_tokens is a safety net: if the model ever gets stuck on a strict
        # schema (see ToolStrategy note below), it fails fast/cheap instead of
        # burning the model's full output budget.
        model = ChatOpenAI(model=MODEL_NAME, temperature=0, max_tokens=1500)

    # response_format=InvestigationJudgment (bare schema) would let create_agent
    # pick ProviderStrategy for models with native structured output (OpenAI,
    # Anthropic, xAI) - it hands the schema to OpenAI's strict json_schema mode.
    # That's usually the more reliable option, but gpt-4o-mini can, in some
    # environments, get stuck generating inside that strict-schema call and
    # run all the way to the completion-token cap without ever emitting valid
    # JSON (openai.LengthFinishReasonError). Wrapping the schema in
    # ToolStrategy(...) forces LangChain to extract the final answer as a
    # normal tool call instead - the same mechanism already working fine for
    # the 5 investigation tools above - which sidesteps that failure mode.
    return create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        response_format=ToolStrategy(InvestigationJudgment),
    )


def render_judgment(j):
    if j is None:
        print("\n[Agent] Did not produce a structured judgment.")
        return
    if hasattr(j, "model_dump"):
        j = j.model_dump()
    print("\n" + "=" * 78)
    print(" INVESTIGATION JUDGMENT")
    print("=" * 78)
    print(f" Risk level   : {j.get('risk_level', '?')}")
    print(f" Confidence   : {j.get('confidence', '?')}")
    print(f" Headline     : {j.get('headline', '')}")
    print(" Evidence:")
    for e in j.get("evidence", []):
        print(f"   - {e}")
    print(f" Recommended action: {j.get('recommended_action', '')}")
    print("=" * 78)


def run_investigation(expense_id, agent=None):
    txn = TRANSACTIONS_BY_ID.get(expense_id)
    if not txn:
        sys.exit(f"No transaction {expense_id} in {EXPENSES_CSV}")

    if agent is None:
        agent = build_agent()

    print("=" * 78)
    print(" LLM INVESTIGATOR AGENT (LangChain / LangGraph) - LIVE INVESTIGATION")
    print("=" * 78)
    print(f" Model            : {MODEL_NAME}")
    print(f" Investigating    : {expense_id}  ({txn['employee']}, {txn['vendor']}, "
          f"Rs.{float(txn['amount']):,.0f})")
    print("-" * 78)

    inputs = {
        "messages": [
            {"role": "user", "content": f"Investigate transaction {expense_id}. Start by pulling its full record."}
        ]
    }

    final_state = None
    seen_message_ids = set()
    for state in agent.stream(inputs, stream_mode="values"):
        final_state = state
        messages = state.get("messages", [])
        if not messages:
            continue
        last = messages[-1]
        msg_id = getattr(last, "id", None) or id(last)
        if msg_id in seen_message_ids:
            continue
        seen_message_ids.add(msg_id)

        msg_type = getattr(last, "type", "")
        if msg_type == "ai":
            tool_calls = getattr(last, "tool_calls", None) or []
            for tc in tool_calls:
                args_str = ", ".join(f"{k}={v!r}" for k, v in (tc.get("args") or {}).items())
                print(f"\n[Agent] calls {tc['name']}({args_str})")
            if not tool_calls and last.content:
                print(f"\n[Agent] {last.content}")
        elif msg_type == "tool":
            print(f"[Tool result: {last.name}]")
            try:
                print(json.dumps(json.loads(last.content), indent=2))
            except (TypeError, ValueError):
                print(last.content)

    judgment = (final_state or {}).get("structured_response")
    render_judgment(judgment)
    return judgment


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 langchain_investigator_agent.py <EXPENSE_ID>\n"
                  "Example: python3 langchain_investigator_agent.py EXP-1015")
    run_investigation(sys.argv[1])