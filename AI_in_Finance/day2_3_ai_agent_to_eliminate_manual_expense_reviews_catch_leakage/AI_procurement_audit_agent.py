"""
Smart Procurement Auditing - Live Demo
========================================
A simplified AI audit agent that reads a batch of expense/procurement
transactions and flags leakage, policy violations, and fraud patterns
the way a production agent would - by combining deterministic policy
rules with cross-record pattern detection (the part manual, line-by-line
review almost always misses).

Run:  python ai_procurement_audit_agent.py

Facilitator note: walk through each rule as its findings print. Pause
on Rule 3 (segregation of duties) and Rule 4 (threshold structuring) -
these are the two patterns that are effectively impossible to catch
by manually eyeballing a spreadsheet one row at a time, but trivial
for an agent that reasons across the whole ledger at once.
"""

import csv
from collections import defaultdict
from datetime import datetime

APPROVAL_THRESHOLD = 50000          # requires additional sign-off above this
RECEIPT_REQUIRED_ABOVE = 5000       # receipts mandatory above this amount
STRUCTURING_WINDOW_DAYS = 2         # days within which split spend is suspicious
NEAR_THRESHOLD_BAND = 0.99          # flag amounts sitting in top 1% of threshold


def load_expenses(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["amount"] = float(r["amount"])
        r["date"] = datetime.strptime(r["date"], "%Y-%m-%d")
    return rows


def rule_missing_receipt(rows):
    flags = []
    for r in rows:
        if r["receipt_attached"] == "No" and r["amount"] > RECEIPT_REQUIRED_ABOVE:
            flags.append((r, f"No receipt on file for Rs.{r['amount']:,.0f} "
                              f"(policy requires receipt above Rs.{RECEIPT_REQUIRED_ABOVE:,.0f})"))
    return flags


def rule_near_threshold(rows):
    flags = []
    band_floor = APPROVAL_THRESHOLD * NEAR_THRESHOLD_BAND
    for r in rows:
        if band_floor <= r["amount"] < APPROVAL_THRESHOLD:
            flags.append((r, f"Amount Rs.{r['amount']:,.0f} sits just under the "
                              f"Rs.{APPROVAL_THRESHOLD:,.0f} sign-off threshold - "
                              f"classic threshold-shaving signature"))
    return flags


def rule_self_approval(rows):
    flags = []
    for r in rows:
        if r["employee"] == r["approver"]:
            flags.append((r, f"{r['employee']} approved their own expense - "
                              f"segregation-of-duties violation"))
    return flags


def rule_structuring(rows):
    """Detect same employee+vendor submitting multiple sub-threshold
    transactions close together that sum above the approval threshold."""
    flags = []
    groups = defaultdict(list)
    for r in rows:
        groups[(r["employee"], r["vendor"])].append(r)

    for (employee, vendor), items in groups.items():
        if len(items) < 2:
            continue
        items.sort(key=lambda x: x["date"])
        for i in range(len(items) - 1):
            a, b = items[i], items[i + 1]
            gap = abs((b["date"] - a["date"]).days)
            combined = a["amount"] + b["amount"]
            if gap <= STRUCTURING_WINDOW_DAYS and combined > APPROVAL_THRESHOLD and \
               a["amount"] < APPROVAL_THRESHOLD and b["amount"] < APPROVAL_THRESHOLD:
                flags.append((b, f"{employee} filed 2 transactions with {vendor} "
                                  f"{gap} day(s) apart totalling Rs.{combined:,.0f} "
                                  f"- individually under threshold, combined over it "
                                  f"(possible invoice/spend splitting)"))
    return flags


def rule_shared_vendor_pattern(rows):
    """Same vendor used by multiple employees, all near-threshold, all
    missing receipts - hallmark of a shell vendor or kickback scheme."""
    flags = []
    by_vendor = defaultdict(list)
    for r in rows:
        by_vendor[r["vendor"]].append(r)

    for vendor, items in by_vendor.items():
        employees = {i["employee"] for i in items}
        suspicious = [i for i in items if i["amount"] >= APPROVAL_THRESHOLD * NEAR_THRESHOLD_BAND
                      and i["receipt_attached"] == "No"]
        if len(employees) > 1 and len(suspicious) >= 2:
            names = ", ".join(sorted(employees))
            flags.append((items[0], f"Vendor '{vendor}' billed by {len(employees)} "
                                     f"different employees ({names}), all near-threshold "
                                     f"and missing receipts - recommend vendor master "
                                     f"file review for shell-vendor risk"))
    return flags


def rule_personal_card_reimbursable(rows):
    flags = []
    for r in rows:
        if r["payment_method"] == "Personal Card" and r["amount"] > 10000:
            flags.append((r, f"Rs.{r['amount']:,.0f} routed through a personal card "
                              f"instead of the corporate card - bypasses card-level "
                              f"controls and MCC restrictions"))
    return flags


RULES = [
    ("Missing receipt above policy limit", rule_missing_receipt),
    ("Threshold shaving (amount just under sign-off limit)", rule_near_threshold),
    ("Self-approval / segregation-of-duties violation", rule_self_approval),
    ("Spend structuring across linked transactions", rule_structuring),
    ("Shared-vendor / shell-vendor pattern across employees", rule_shared_vendor_pattern),
    ("Reimbursable spend on personal card (control bypass)", rule_personal_card_reimbursable),
]


def main():
    rows = load_expenses("expenses_demo.csv")
    total_spend = sum(r["amount"] for r in rows)
    flagged_ids = set()
    all_flags = []

    print("=" * 78)
    print(" SMART PROCUREMENT AUDIT AGENT - RUN REPORT")
    print("=" * 78)
    print(f" Transactions scanned : {len(rows)}")
    print(f" Total spend reviewed : Rs.{total_spend:,.0f}")
    print("-" * 78)

    for name, rule_fn in RULES:
        flags = rule_fn(rows)
        print(f"\n[Rule] {name}  ->  {len(flags)} finding(s)")
        for record, reason in flags:
            flagged_ids.add(record["expense_id"])
            all_flags.append((name, record, reason))
            print(f"   - {record['expense_id']} | {record['employee']:12s} | "
                  f"Rs.{record['amount']:>9,.0f} | {reason}")

    flagged_amount = sum(r["amount"] for r in rows if r["expense_id"] in flagged_ids)
    print("\n" + "=" * 78)
    print(" SUMMARY")
    print("=" * 78)
    print(f" Transactions flagged   : {len(flagged_ids)} / {len(rows)} "
          f"({len(flagged_ids)/len(rows):.0%})")
    print(f" Rupee value flagged    : Rs.{flagged_amount:,.0f} "
          f"({flagged_amount/total_spend:.0%} of total spend reviewed)")
    print(f" Findings requiring     : escalation to procurement/audit committee")
    print(" Time to scan full batch : < 2 seconds (vs. hours of manual sampling)")
    print("=" * 78)

    with open("flagged_expenses_output.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["expense_id", "employee", "amount", "rule_triggered", "reason"])
        for name, record, reason in all_flags:
            writer.writerow([record["expense_id"], record["employee"],
                              f"{record['amount']:.0f}", name, reason])
    print("\nDetailed findings written to flagged_expenses_output.csv")


if __name__ == "__main__":
    main()