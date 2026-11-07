# Finance CSV to Excel reports

Requires Python 3.10 or newer. No third-party packages are required.

Keep these two files together:

- `process_finance.py`
- `report_template.xlsx`

The template is a copy of the approved Excel report. The script preserves its fonts,
column widths, table styles, number formats, loss highlighting, chart types, chart
colors, chart titles and positions. It replaces the data and formulas and updates
the three editable charts. This avoids differences caused by recreating the design
with a different Excel library. Do not delete or redesign the template sheets.

## Run

Place CSV files in `incoming`, beside the script. In that folder run:

```powershell
python process_finance.py
```

If Windows uses the Python launcher, use `py process_finance.py` instead.

To process a different folder while retaining the template beside the script:

```powershell
python process_finance.py --root "C:\path\to\finance_folder"
```

Reports are saved as `outgoing/<input_name>_report.xlsx`. Successful originals move
to `archive`. The script verifies the saved workbook before archiving and records
its source name, SHA-256 hash, report location, counts, totals and status in
`processing_record.json`. It recognizes the processing record created for the
approved report. Already archived or recorded inputs are skipped. Existing reports
are never overwritten. If no files are new, reports are not recreated.

Do not run multiple copies simultaneously against the same folder. Keep the
processing record with its incoming/outgoing/archive folders.

## Workbook behavior

- `processed`: title in A2, total revenue in B4, total profit in B5, record counts
  in E4:E5, detail headers in row 8, department summary in M8:Q8.
- `raw data`: every original CSV record, retaining field text and original column order.
- `invalid sheet`: rejected records with physical CSV `source_line` and every
  rejection reason in `comments`. A multiline record uses its starting line.
- Revenue, cost, profit, margin and department summaries are editable Excel
  formulas, with calculated cached values available before Excel opens the file.
- The charts use worksheet references, so editing the data updates the figures
  when Excel recalculates. Adding brand-new rows or departments manually requires
  extending the summary formulas and chart ranges; rerunning on a new CSV does
  this automatically.
- No frozen columns or split panes. Charts move down when more than five
  departments need additional summary rows.
- No accepted records: totals are zero, the accepted table has a blank placeholder
  row and the three charts have no data. This row is not counted as an accepted record.
- CSV encoding is UTF-8, with or without a BOM. Quoted commas and multiline fields
  are supported. Structurally unreadable CSVs, missing/duplicate headers, or text
  Excel cannot preserve cause failure; the original remains available for review.

Blank required values are rejected. Dates require a real calendar date in
YYYY-MM-DD form. Units require positive integers; prices and costs require finite
nonnegative numbers. Only an accepted row reserves its transaction ID; the first
valid occurrence wins. Rejected rows do not reserve IDs. An input with missing
required columns fails as a whole.

## Verification performed

For the archived sample, the Python report matched the approved workbook's
populated cell values, formulas, cell styles, table ranges, chart counts and chart
positions. The style definitions and drawing layout are preserved unchanged.

The sample result is 20 accepted records, 8 rejected records, INR 1,145,000 revenue
and INR 576,650 profit. Additional checks covered duplicate IDs after invalid
occurrences, multiple rejection reasons, source lines, zero revenue, no records,
all-rejected files, extra fields, 12 departments and skipping on a second run.

The output is not byte-for-byte identical to the approved XLSX: ZIP metadata and
XML serialization differ, and the script populates chart caches and enables Excel
recalculation. The approved workbook's design is retained. Tests did not involve
opening a desktop Excel application.

The script does not send email or create email drafts.
