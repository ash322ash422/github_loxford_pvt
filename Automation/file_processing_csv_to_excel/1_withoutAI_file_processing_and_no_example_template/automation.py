"""Finance CSV -> validated Excel dashboard -> outgoing folder. Python 3.10+."""
import argparse
import csv
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation
import xlsxwriter

ROOT = Path(__file__).resolve().parent
FIELDS = ['transaction_id', 'date', 'department', 'category', 'units', 'unit_price', 'unit_cost']


def setup():
    for name in ['incoming', 'outgoing', 'archive', 'failed', 'logs', 'state']:
        (ROOT / name).mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.FileHandler(ROOT / 'logs/automation.log', encoding='utf-8')])


def show_progress(message):
    print(message, flush=True)


def read_rows(path):
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError('CSV headers must be exactly: ' + ','.join(FIELDS))
        raw = list(reader)
    good, bad, seen = [], [], set()
    for line, row in enumerate(raw, 2):
        reasons = []
        if None in row or any(v is None for v in row.values()):
            reasons.append('Incorrect number of CSV fields')
        clean = {k: (row.get(k) or '').strip() for k in FIELDS}
        for key, value in clean.items():
            if not value:
                reasons.append(f'Missing {key}')
        try:
            date = datetime.strptime(clean['date'], '%Y-%m-%d')
        except ValueError:
            reasons.append('Invalid date; expected YYYY-MM-DD')
        numbers = {}
        for key in ['units', 'unit_price', 'unit_cost']:
            try:
                value = Decimal(clean[key])
                if not value.is_finite() or value < 0 or (key == 'units' and (value <= 0 or value != value.to_integral_value())):
                    raise ValueError()
                if value > Decimal('1000000000'):
                    raise ValueError()
                numbers[key] = float(value)
            except (InvalidOperation, ValueError):
                reasons.append(f'Invalid {key}; expected ' + ('a positive whole number' if key == 'units' else 'a nonnegative number') + ' up to 1 billion')
        if clean['transaction_id'] in seen:
            reasons.append('Duplicate transaction_id within file')
        if reasons:
            bad.append(([row.get(k) or '' for k in FIELDS], line, '; '.join(reasons)))
        else:
            seen.add(clean['transaction_id'])
            good.append([clean['transaction_id'], date, clean['department'], clean['category'], numbers['units'], numbers['unit_price'], numbers['unit_cost']])
    return raw, good, bad


def create_report(source, target, progress=None):
    if progress:
        progress('Checking required fields, dates, numbers and duplicate records...')
    raw, good, bad = read_rows(source)
    if progress:
        progress(f'Data check complete: {len(good)} accepted, {len(bad)} invalid out of {len(raw)} records.')
        progress('Creating Excel sheets, formulas and department charts...')
    # Disable automatic formula and hyperlink interpretation for untrusted CSV strings.
    with xlsxwriter.Workbook(target, {'strings_to_formulas': False, 'strings_to_urls': False}) as book:
        navy, teal = '#183153', '#008C95'
        header = book.add_format({'bold': True, 'bg_color': navy, 'font_color': 'white', 'text_wrap': True})
        title = book.add_format({'bold': True, 'font_size': 22, 'font_color': navy})
        money = book.add_format({'num_format': '"INR "#,##0.00;[Red]("INR "#,##0.00)'})
        pct = book.add_format({'num_format': '0.0%'})
        date_fmt = book.add_format({'num_format': 'dd mmm yyyy'})
        integer = book.add_format({'num_format': '#,##0'})
        note = book.add_format({'font_color': '#536475', 'text_wrap': True})
        dashboard = book.add_worksheet('processed')
        raw_sheet = book.add_worksheet('raw data')
        missing = book.add_worksheet('invalid sheet')
        for sheet in [dashboard, raw_sheet, missing]:
            sheet.hide_gridlines(2)
            sheet.set_tab_color(teal)
            sheet.set_default_row(21)
            sheet.set_column('A:A', 22)
            sheet.set_column('B:D', 20)
            sheet.set_column('E:K', 19)
        dashboard.merge_range('A1:K2', 'FINANCE | AUTOMATED REPORT', title)
        dashboard.merge_range('A3:K3', f'Source: {source.name} | Currency: INR | Synthetic demonstration data', note)
        dashboard.write_row('A5', ['Source records', len(raw), 'Accepted', len(good), 'Rejected', len(bad)])
        dashboard.merge_range('A6:K6', 'Revenue = units × price | Cost = units × unit cost | Profit = revenue − cost | Margin = profit / revenue', note)
        headers = FIELDS + ['revenue', 'cost', 'profit', 'margin']
        start = 24
        dashboard.write('H5', 'Total revenue', header)
        dashboard.write('J5', 'Total profit', header)
        total_revenue = sum(r[4] * r[5] for r in good)
        total_profit = sum(r[4] * (r[5] - r[6]) for r in good)
        dashboard.write_formula('I5', f'=SUM(H26:H{25+len(good)})' if good else '=0', money, total_revenue)
        dashboard.write_formula('K5', f'=SUM(J26:J{25+len(good)})' if good else '=0', money, total_profit)
        dashboard.write_row(start, 0, headers, header)
        for i, values in enumerate(good, start + 1):
            dashboard.write_row(i, 0, values)
            dashboard.write_datetime(i, 1, values[1], date_fmt)
            r = i + 1
            revenue, cost = values[4]*values[5], values[4]*values[6]
            for col, formula, cached, fmt in [(7, f'=E{r}*F{r}', revenue, money), (8, f'=E{r}*G{r}', cost, money), (9, f'=H{r}-I{r}', revenue-cost, money), (10, f'=IFERROR(J{r}/H{r},0)', (revenue-cost)/revenue if revenue else 0, pct)]:
                dashboard.write_formula(i, col, formula, fmt, cached)
        dashboard.set_column('E:E', 16, integer)
        dashboard.set_column('F:J', 21, money)
        dashboard.set_column('K:K', 16, pct)
        dashboard.freeze_panes(start + 1, 0)
        if good:
            dashboard.add_table(start, 0, start + len(good), 10, {'name': 'FinanceData', 'style': 'Table Style Medium 2', 'columns': [{'header': h} for h in headers]})
            dashboard.conditional_format(start+1, 9, start+len(good), 9, {'type': 'cell', 'criteria': '<', 'value': 0, 'format': book.add_format({'bg_color': '#FCE4E4', 'font_color': '#9C0006'})})
        # Visible, formula-linked summary supports all three editable Excel charts.
        dashboard.write_row('M24', ['Department', 'Revenue', 'Cost', 'Profit', 'Profit (INR lakh)'], header)
        departments = sorted({r[2] for r in good})
        for i, dept in enumerate(departments, 24):
            dashboard.write(i, 12, dept)
            for col, data_col in [(13, 'H'), (14, 'I'), (15, 'J')]:
                cached = sum((r[4]*r[5] if col == 13 else r[4]*r[6] if col == 14 else r[4]*(r[5]-r[6])) for r in good if r[2] == dept)
                dashboard.write_formula(i, col, f'=SUMIF($C$26:$C${25+len(good)},M{i+1},${data_col}$26:${data_col}${25+len(good)})', money, cached)
            profit = sum(r[4]*(r[5]-r[6]) for r in good if r[2] == dept)
            dashboard.write_formula(i, 16, f'=P{i+1}/100000', book.add_format({'num_format': '0.00'}), profit / 100000)
        dashboard.set_column('M:Q', 22)
        if departments:
            for kind, anchor, chart_title, columns in [('column', 'A8', 'Revenue and cost by department', [13,14]), ('bar', 'F8', 'Profit by department (INR lakh)', [16]), ('doughnut', 'K8', 'Revenue share by department', [13])]:
                chart = book.add_chart({'type': kind})
                for col in columns:
                    chart.add_series({'name': ['processed',23,col], 'categories': ['processed',24,12,23+len(departments),12], 'values': ['processed',24,col,23+len(departments),col]})
                chart.set_title({'name': chart_title})
                if kind == 'bar':
                    chart.set_x_axis({'name': 'Profit (INR lakh)', 'num_format': '0.00'})
                chart.set_style(10)
                chart.set_size({'width': 470, 'height': 280})
                dashboard.insert_chart(anchor, chart)
        else:
            dashboard.write('A9', 'No valid records; charts require at least one accepted row.')
        for sheet, rows, labels in [(raw_sheet, [[r.get(k) or '' for k in FIELDS] + [json.dumps(r.get(None)) if None in r else ''] for r in raw], FIELDS + ['extra CSV fields']), (missing, [r + [line, reason] for r,line,reason in bad], FIELDS + ['source_line', 'comments'])]:
            sheet.write_row(0, 0, labels, header)
            for i, row in enumerate(rows, 1):
                sheet.write_row(i, 0, row)
            sheet.freeze_panes(1, 0)
            sheet.autofilter(0, 0, len(rows), len(labels)-1)
        missing.set_column('I:I', 85, note)
        for i in range(1,len(bad)+1):
            missing.set_row(i, 60)
        dashboard.activate()
    return {'source_rows': len(raw), 'accepted_rows': len(good), 'rejected_rows': len(bad)}


def run_once():
    for source in sorted((ROOT/'incoming').glob('*.csv')):
        # Only consume stable files. Producers should copy as .part then rename to .csv.
        before = source.stat()
        time.sleep(1)
        if (before.st_size, before.st_mtime_ns) != (source.stat().st_size, source.stat().st_mtime_ns):
            continue
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        marker = ROOT/'state'/f'{digest}.json'
        archived = ROOT/'archive'/f'{source.stem}_{digest[:12]}.csv'
        if marker.exists():
            shutil.move(str(source), str(archived))
            logging.info('Skipped previously processed content: %s', source.name)
            show_progress(f'Skipped {source.name}: this file was already processed.')
            continue
        report = ROOT/'outgoing'/f'{source.stem}_{digest[:12]}.xlsx'
        temporary = report.with_suffix('.tmp.xlsx')
        try:
            show_progress(f'Processing file: {source.name}')
            stats = create_report(source, temporary, progress=show_progress)
            temporary.replace(report)
            marker.write_text(json.dumps({'source':source.name,'report':report.name,**stats}, indent=2), encoding='utf-8')
            shutil.move(str(source), str(archived))
            logging.info('Created %s: %s', report.name, stats)
            show_progress(f'Report saved: {report}')
            show_progress('Original CSV archived. Processing complete.')
        except Exception:
            temporary.unlink(missing_ok=True)
            logging.exception('Processing failed for %s', source.name)
            shutil.move(str(source), str(ROOT/'failed'/f'{source.stem}_{digest[:12]}.csv'))
            show_progress(f'Could not process {source.name}. The CSV is in failed. See logs/automation.log for details.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watch', action='store_true', help='Poll incoming continuously')
    parser.add_argument('--interval', type=int, default=10)
    args = parser.parse_args()
    setup()
    lock = ROOT/'state/run.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        parser.error('Another instance is running. If it crashed, remove state/run.lock after checking.')
    os.close(fd)
    try:
        show_progress(f'Checking for CSV files in: {ROOT / "incoming"}')
        if args.watch:
            show_progress('Watching for new files. Press Ctrl+C to stop.')
        elif not any((ROOT/'incoming').glob('*.csv')):
            show_progress('No CSV files found. Add a file to incoming and run again.')
        while True:
            run_once()
            if not args.watch:
                break
            time.sleep(max(2,args.interval))
    except KeyboardInterrupt:
        logging.info('Stopped')
        show_progress('Folder monitoring stopped.')
    except Exception:
        logging.exception('Automation stopped; check logs and configuration before retrying')
        show_progress('Automation stopped because of an error. See logs/automation.log for details.')
        raise SystemExit(1)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    main()

