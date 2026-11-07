# Finance file processing automation

A Python demo that turns an incoming finance CSV into a polished Excel report saved in `outgoing`. All sample records are fictional; amounts use INR. The workflow runs locally and ends when the report is saved.

## Quick start

Requires Python 3.10 or newer. Run these commands in this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe automation.py
```

The supplied sample has already been processed as a demonstration. See `outgoing` for the Excel reports, and `archive` for the original sample CSV. To reproduce from scratch, use a fresh copy of this project with the archived CSV placed in `incoming` and an empty `state` folder. Do not clear production state casually: it prevents duplicate processing.

For continuous folder monitoring:

```powershell
.\.venv\Scripts\python.exe automation.py --watch --interval 10
```

Stop with Ctrl+C. Alternatively, use Windows Task Scheduler to run the full path to `.venv\Scripts\python.exe`, with the full path to `automation.py` as its argument, every few minutes. Paths resolve relative to the script, so the working directory does not matter. Use either a scheduled one-shot run or the continuous watcher. Concurrent instances are blocked by a lock file.

## What happens automatically

The console shows only important progress: the file being processed, validation counts, report creation, the saved report location, and archival completion. It also explains skipped duplicates, an empty incoming folder, and processing failures. Monitoring stays quiet between files. Detailed errors remain in `logs/automation.log`.

1. Discover `.csv` files directly in `incoming`. A short stability check avoids reading files that are visibly changing. Producers should write a `.part` file, close it, then rename to `.csv` for reliable handoff.
2. Preserve every source record on **raw data**, as literal text, including unexpected extra fields. The archived original retains the exact source bytes.
3. Validate required fields, dates, finite numeric values and duplicate transaction IDs within the file. Put rejected records on **invalid sheet**, with their source line and all applicable reasons in **comments**. Structurally invalid files go to `failed` with details in the log.
4. Put accepted, typed records on **processed**, alongside Excel formulas for revenue, cost, profit and margin, and a department summary. Create three native Excel charts: revenue versus cost, profit, and revenue share. Apply filters, table striping, frozen panes, currency/date/percentage formats and loss highlighting. A negative profit is valid and highlighted. For a file with no accepted rows, show a clear message instead of meaningless charts.
5. Save the workbook in **outgoing**, archive the input, and record processing counts and a SHA-256 content fingerprint. Previously processed content is skipped, even if renamed. A changed file creates a new report.

The included 28-row sample produces **20 accepted and 8 rejected records**, including missing fields, an impossible date, nonnumeric units, a negative price, a duplicate ID, zero units and NaN. Accepted revenue totals **INR 1,145,000**, cost **INR 568,350**, and profit **INR 576,650**.

## CSV contract

UTF-8 CSV, with this exact header order:

```csv
transaction_id,date,department,category,units,unit_price,unit_cost
```

All seven fields are required. Dates must parse as `YYYY-MM-DD`. Units must be positive whole numbers. Price and cost must be finite, nonnegative numbers. Numeric inputs cannot exceed one billion. Zero price or cost is allowed; a zero-revenue row has a margin of zero. Surrounding whitespace is trimmed for validation. The first valid occurrence of an ID is accepted; subsequent valid occurrences are rejected. Duplicate checks apply within each CSV; file fingerprints handle identical repeat files. Each record represents a sale, not a ledger debit or credit. Adapt these rules for a different finance use case.

## Project contents

- `automation.py`: validation, report creation, monitoring and archival.
- `requirements.txt`: single external dependency, XlsxWriter.
- `incoming`: drop new CSV files here.
- `outgoing`: generated Excel reports.
- `archive`: processed source files.
- `failed`: files that could not be processed.
- `state`: content fingerprints and single-instance lock.
- `logs/automation.log`: operational history.
- `test_automation.py`: isolated checks for validation and workbook contents.

## Verification and demonstration

The processed sheet includes total revenue in `I5` and total profit in `K5`, both linked to the detail formulas. The profit-by-department chart uses INR lakh (1 lakh = 100,000 INR); its visible supporting column divides departmental profit by 100,000. Only rows are frozen, so there is no frozen-column divider between B and C.

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```

Open the sample report in Excel to explore the charts and change a processed numeric input to see formulas and department summaries update. Formula values are cached so initial previews show results. XlsxWriter does not calculate formulas; this program computes matching initial cached values, and Excel recalculates on opening. New records require another CSV run; chart/table ranges cover the records from that run.

For a presentation, show the archived CSV, then the processed dashboard and invalid sheet, and finally the saved report in outgoing. Compare your measured manual time for importing, cleaning, calculating, formatting and charting with the run duration in the log. For example, a measured 20-minute manual task versus a 10-second run saves about 19 minutes 50 seconds per file; those figures are illustrative, not a benchmark. Additional automation includes an audit trail, repeat-file prevention, error isolation, and automatic archival.

For production, set appropriate folder access and retention, and monitor the process. This demo loads each CSV in memory and is intended for modest files. It does not perform accounting reconciliation or validate department/category names against an external master list. Keep the original archive for audit and recovery. If a process is forcibly terminated, verify it has stopped before removing `state/run.lock`.


