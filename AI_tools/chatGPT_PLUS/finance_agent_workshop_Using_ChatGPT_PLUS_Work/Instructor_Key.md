# Instructor key — keep separate from the initial analysis

This key contains the answers for the fictional Meridian Business Services exercise. Upload only Finance_Agent_Practice.xlsx at the beginning. Share this key with an independent reviewer after the first analysis is finished.

## The clarification to give when asked

Copy this response into the analysis conversation:

```text
For this fictional exercise, I confirm that transaction J-1047, Finance / Training / August 2026, has an expense amount of INR 30,000. This is the confirmed ledger value for the missing field. Add it only in your cleaned working data and clarification log. Preserve the original blank in the raw source. Continue with the agreed analysis.
```

Do not give the agent the expected grand totals before it does its own calculation. Before receiving the response above, the agent must treat the blank as unknown. It can show a known-value subtotal of INR 25,481,000 after duplicate/cutoff cleaning, but the final total and affected Finance/Training results remain incomplete.

## Data-quality answers

| Case | Expected treatment |
|---|---|
| Budget population | 72 rows and 72 unique month/department/category keys |
| Actuals source | 76 raw journal rows, including one blank amount |
| Exact duplicate J-1039 | Two identical copies of the INR 400,000 Technology / Software / August journal line. Retain one and log removal of one INR 400,000 row. |
| J-2003 | INR 90,000 Sales / Travel in October. Exclude from July–September, retain in source and reconciliation. |
| J-1047 | Blank Finance / Training / August amount. Request clarification. Confirmed amount is INR 30,000. |
| Financ department label | Map to Finance as authorized. One row, Finance / Facilities / September, INR 104,000. No amount change. |
| INV-7-2-2 | Two valid Technology / Software / July service lines with distinct IDs: J-1015 INR 250,000 and J-2001 INR 100,000. Keep both. July actual is INR 350,000. |
| J-2002 / CN-TECH-09 | INR (50,000) September Technology / Software credit. Keep negative. September net software actual is INR 430,000. |
| Final actual population | 74 rows after removing one duplicate and one October row. Filling the missing value and mapping the alias do not change the row count. |
| Coverage | 72 aggregated actual keys match 72 budget keys after cleaning. No additional unmatched keys. |

### Amount bridge (INR)

| Step | Amount |
|---|---:|
| Raw total of known numeric amounts, blank excluded | 25,971,000 |
| Remove one duplicate J-1039 | (400,000) |
| Exclude October J-2003 | (90,000) |
| Add confirmed J-1047 amount | 30,000 |
| Cleaned July–September actual | **25,511,000** |

The INR (50,000) supplier credit is already included in the raw numeric total. Do not subtract it a second time in the bridge.

## Final control totals (INR)

| Metric | Expected |
|---|---:|
| Quarter budget | 24,410,000 |
| Quarter actual | 25,511,000 |
| Actual less budget | **1,101,000 unfavorable** |
| Quarter percentage variance | **4.5104465383%** (display 4.5%) |

| Month | Budget | Actual | Variance |
|---|---:|---:|---:|
| July 2026 | 8,150,000 | 8,132,000 | (18,000) |
| August 2026 | 8,150,000 | 8,459,000 | 309,000 |
| September 2026 | 8,110,000 | 8,920,000 | 810,000 |
| Total | **24,410,000** | **25,511,000** | **1,101,000** |

| Department | Quarter budget | Quarter actual | Variance | Material at department level? |
|---|---:|---:|---:|---|
| Sales | 6,330,000 | 6,531,000 | 201,000 | No, percentage is below 10% |
| Marketing | 4,340,000 | 4,927,000 | 587,000 | Yes, approximately 13.5% |
| Technology | 9,150,000 | 9,513,000 | 363,000 | No, percentage is below 10% |
| Finance | 4,590,000 | 4,540,000 | (50,000) | No |
| Total | **24,410,000** | **25,511,000** | **1,101,000** | |

## Expected monthly exceptions

Strict materiality is ABS(variance) > INR 100,000 AND ABS(variance/budget) > 10%, evaluated using unrounded numbers. Nonzero spend against a zero budget is a separate Unbudgeted flag.

| Month / department / category | Budget | Actual | Variance | Percentage | Label |
|---|---:|---:|---:|---:|---|
| August / Sales / Travel | 200,000 | 340,000 | 140,000 | 70.0% | Material unfavorable |
| September / Marketing / Professional fees | 180,000 | 600,000 | 420,000 | 233.3% | Material unfavorable |
| September / Technology / Software | 300,000 | 430,000 | 130,000 | 43.3% | Material unfavorable |
| September / Marketing / Training | 0 | 120,000 | 120,000 | n.a. | Unbudgeted |

Exactly three monthly keys pass normal materiality; one additional monthly key is Unbudgeted. August Technology / Software is INR 100,000 above budget, so it does not pass the strict monetary threshold. July Finance / Professional fees is INR 100,000 below budget, also not material under the strict rule. Do not change > to >=.

## Expected quarterly department/category exceptions

| Department / category | Budget | Actual | Variance | Percentage |
|---|---:|---:|---:|---:|
| Sales / Travel | 600,000 | 742,000 | 142,000 | 23.7% |
| Marketing / Professional fees | 540,000 | 971,000 | 431,000 | 79.8% |
| Marketing / Training | 80,000 | 200,000 | 120,000 | 150.0% |
| Technology / Software | 900,000 | 1,180,000 | 280,000 | 31.1% |

All four are material unfavorable. The quarter Marketing / Training budget is positive even though September's budget is zero. There are no quarter department/category Unbudgeted keys. Only Marketing is material at the quarter department level. These views overlap; adding their exception amounts together would double-count spend.

## Evidence and interpretation

- E-01 supports the source's explanation of additional Sales travel in August. No price/volume split can be calculated from the supplied journal amounts alone.
- E-02 attributes September Marketing professional fees to a one-off launch agency fee. Do not extrapolate the whole fee into recurring monthly expense without a further assumption.
- E-03 supports the September Technology credit. E-07 attributes August license cost to additional licenses, but gives no quantities or unit rates for a numerical price/volume bridge.
- E-04 explains the two legitimate July invoice lines.
- E-05 says advisory work shifted to October. The July underspend is a timing item, not demonstrated permanent savings. The October travel line is unrelated and cannot be used as evidence that the advisory work was posted.
- E-06 explains September unplanned training according to the source note.
- A strong report distinguishes calculated financial effects, attributed source explanations, and remaining questions. Suggested actions and owners are recommendations, not completed follow-ups.


