# Finance agent workshop: prompts and run order

Use the fictional Finance_Agent_Practice.xlsx workbook. Upload only that workbook for the analysis exercise. Keep Instructor_Key.md separate until the testing phase. No real corporate data is needed.

Suggested timing: 5 minutes for the brief, 10 for setup and inspection, 15 for analysis and reporting, 10 for independent testing, and 10 for improving and rerunning the instructions. Allow extra time for tool execution.

**The exercise demonstrates an agent workflow: objective, instructions, tools, data, execution, clarification, verification, and revision.**

### Important
 Calling a chatbot an “agent” does not establish that it used tools. Ask it to show the files and calculations it actually produced. If file-analysis or file-creation tools are unavailable in the selected experience, do not claim they ran.

## Prompt 1 — Define the agent and inspect the inputs

```text
Act as an FP&A analysis agent for the fictional Meridian Business Services Pvt Ltd. Your objective is to analyze July–September 2026 operating expenses against budget, identify material exceptions, and prepare a traceable CFO report.

Use the attached workbook as the source. Read Brief first, then Budget, Actuals, and Evidence. Use file-analysis/calculation tools for arithmetic. Preserve raw sheets and put cleaning and calculations in separate output sheets. Do not use external research for this exercise.

Calculation and data rules:
1. Work in INR, whole rupees, accrual operating expenses excluding GST. Include only July, August, and September 2026 posting months.
2. Join using month + canonical department + category. Budget must have one unique row per key, with 72 expected keys. Aggregate actual journal lines to that grain before comparing. Check coverage and unmatched keys.
3. An exact repeated row with the same Transaction ID is one transaction: retain one copy and log the removal. A repeated ID with conflicting values requires clarification. Different Transaction IDs sharing a document reference can be valid separate lines. Do not deduplicate on invoice reference or amount alone.
4. Map Financ to Finance, as authorized in Brief. Log this change. Ask about other unmapped labels.
5. Keep credits negative. A blank amount is unknown, not zero. Do not infer missing amounts from budget, trends, or totals. Ask me for confirmation and record my response without changing the raw data. Show affected results as incomplete until resolved. Continue unaffected checks while waiting.
6. Variance = actual minus budget. Positive expense variance is unfavorable, negative is favorable, and zero is on budget. Percentage variance = variance / budget. With zero budget, display n.a. and separately label any nonzero actual as Unbudgeted.
7. For nonzero budgets, a material exception requires BOTH ABS(variance) > 100000 AND ABS(percentage variance) > 10%. Use unrounded values and strict greater-than comparisons. Evaluate monthly department/category keys, quarterly department/category totals, and quarterly department totals independently. Do not add flagged amounts across these overlapping levels.
8. Sum amounts first, then calculate aggregate percentages. Never average row percentages. Missing inputs must remain visible in affected totals; numeric subtotals may be shown only as explicitly provisional.
9. Quantify contributors from the data. Cite transaction IDs and Evidence IDs. Treat source notes as attributed explanations, not independently established causation. State what evidence is missing. Favorable timing variances are not automatically permanent savings.
10. Analyze and draft only. Do not send messages, book journals, or initiate payments.

Required final reporting format:
- Excel workbook with preserved raw inputs, a cleaning/clarification log, cleaned actuals, formula-based monthly department/category detail, quarterly department/category and department summaries, and reconciliation/tests. Use readable currency formats and 1 decimal for displayed percentages. Keep full precision for tests.
- CFO briefing of at most 500 words: overall budget/actual/variance, top contributors, material exceptions and unbudgeted spend, evidence and limitations, and proposed actions with suggested owners clearly labeled as recommendations.
- Reconcile raw known amounts to cleaned in-period actuals, showing exclusions, duplicate removal, and confirmed missing-value additions separately. Reconcile monthly and department summaries to the same grand total.

First inspect the workbook. Report sheet purposes, record counts, data-quality issues, proposed authorized cleaning, and questions requiring my answer. Give a short execution plan. Stop before presenting a final analysis until I ask you to proceed.
```

## Facilitator clarification — Supply only when the agent asks

Read the missing-amount response in the separate Instructor_Key.md. Do not reveal expected totals before the agent calculates them. If the agent does not ask about the blank, ask it to inspect for missing numeric values before proceeding.

