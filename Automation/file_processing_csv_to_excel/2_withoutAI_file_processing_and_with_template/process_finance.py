"""Produce finance reports using the approved workbook as an exact design template.

Python 3.10+, standard library only. Run: python process_finance.py
Keep report_template.xlsx beside this script. --root selects another data folder.
Never overwrites a report. Failed CSVs remain in incoming for review.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
from datetime import date, datetime, timezone
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

S = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
C = 'http://schemas.openxmlformats.org/drawingml/2006/chart'
NS = {'s': S, 'c': C}
for prefix, uri in [('x', S), ('c', C),
                    ('a', 'http://schemas.openxmlformats.org/drawingml/2006/main'),
                    ('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')]:
    ET.register_namespace(prefix, uri)
REQUIRED = ['transaction_id', 'date', 'department', 'category', 'units', 'unit_price', 'unit_cost']
NUMBER = re.compile(r'[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?', re.ASCII)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def column(n):
    text = ''
    while n:
        n, rem = divmod(n - 1, 26)
        text = chr(65 + rem) + text
    return text


def read_csv(data):
    reader = csv.reader(io.StringIO(data.decode('utf-8-sig'), newline=''), strict=True)
    try:
        headers = next(reader)
    except StopIteration:
        raise ValueError('Empty CSV') from None
    if not headers or len(set(headers)) != len(headers):
        raise ValueError('Empty or duplicate column headers')
    missing = [h for h in REQUIRED if h not in headers]
    if missing:
        raise ValueError('Missing required columns: ' + ', '.join(missing))
    rows, accepted, rejected, seen = [], [], [], set()
    while True:
        line = reader.line_num + 1
        try:
            values = next(reader)
        except StopIteration:
            break
        # Preserve blank records as well as ordinary and multiline records.
        rows.append(values)
        obj = {h: (values[headers.index(h)] if headers.index(h) < len(values) else '').strip()
               for h in REQUIRED}
        reasons = []
        if len(values) != len(headers):
            reasons.append(f'Expected {len(headers)} fields; found {len(values)}')
        reasons.extend('Missing required value: ' + h for h in REQUIRED if not obj[h])
        if obj['date']:
            try:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', obj['date'], re.ASCII):
                    raise ValueError()
                date.fromisoformat(obj['date'])
            except ValueError:
                reasons.append('date must be a valid YYYY-MM-DD date')
        if obj['units'] and (not re.fullmatch(r'[0-9]+', obj['units'])
                             or not 0 < int(obj['units']) <= 9007199254740991):
            reasons.append('units must be a positive whole number')
        for h in ['unit_price', 'unit_cost']:
            if obj[h] and (not NUMBER.fullmatch(obj[h]) or not math.isfinite(float(obj[h]))
                           or float(obj[h]) < 0):
                reasons.append(h + ' must be finite and nonnegative')
        if obj['transaction_id'] and obj['transaction_id'] in seen:
            reasons.append('Duplicate transaction_id; first valid occurrence already accepted')
        if reasons:
            rejected.append((values, line, '; '.join(reasons)))
        else:
            seen.add(obj['transaction_id'])
            accepted.append(obj)
    return headers, rows, accepted, rejected


class Sheet:
    def __init__(self, xml):
        self.xml = ET.fromstring(xml)
        self.data = self.xml.find('s:sheetData', NS)
        self.cells = {c.get('r'): copy.deepcopy(c) for c in self.data.iter(f'{{{S}}}c')}
        self.row_attrs = {int(r.get('r')): dict(r.attrib) for r in self.data}
        self.output = {}

    def put(self, address, value=None, formula=None, style_from=None):
        source = self.cells.get(style_from or address)
        attrs = {'r': address, 's': source.get('s', '1') if source is not None else '1'}
        cell = ET.Element(f'{{{S}}}c', attrs)
        if formula is not None:
            ET.SubElement(cell, f'{{{S}}}f').text = formula.removeprefix('=')
            ET.SubElement(cell, f'{{{S}}}v').text = str(value)
        elif isinstance(value, str):
            # Explicit string cells preserve IDs, leading zeroes and literal formulas safely.
            if len(value) > 32767 or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', value):
                raise ValueError(f'Value at {address} cannot be represented safely in Excel')
            cell.set('t', 'inlineStr')
            text = ET.SubElement(ET.SubElement(cell, f'{{{S}}}is'), f'{{{S}}}t')
            text.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            text.text = value
        elif value is not None:
            if not math.isfinite(value):
                raise ValueError(f'Calculation at {address} exceeds Excel numeric limits')
            ET.SubElement(cell, f'{{{S}}}v').text = str(value)
        self.output[address] = cell

    def finish(self):
        self.data.clear()
        grouped = {}
        for address, cell in self.output.items():
            match = re.fullmatch(r'([A-Z]+)(\d+)', address)
            r = int(match[2])
            n = 0
            for ch in match[1]:
                n = n * 26 + ord(ch) - 64
            grouped.setdefault(r, []).append((n, cell))
        for r, cells in sorted(grouped.items()):
            row = ET.SubElement(self.data, f'{{{S}}}row', self.row_attrs.get(r, {'r': str(r)}))
            for _, cell in sorted(cells):
                row.append(cell)
        dim = self.xml.find('s:dimension', NS)
        if dim is not None:
            self.xml.remove(dim)
        return ET.tostring(self.xml, encoding='utf-8', xml_declaration=True)


def make_report(template, target, headers, rows, accepted, rejected):
    with ZipFile(template) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    p = Sheet(parts['xl/worksheets/sheet1.xml'])
    raw = Sheet(parts['xl/worksheets/sheet2.xml'])
    bad = Sheet(parts['xl/worksheets/sheet3.xml'])
    # Keep the approved title, totals area and precise formatting of the opening rows.
    for address, cell in p.cells.items():
        if int(re.search(r'\d+', address)[0]) <= 8:
            p.output[address] = copy.deepcopy(cell)
    width = max([len(headers)] + [len(r) for r in rows])
    raw_headers = headers + [f'extra_field_{i+1}' for i in range(len(headers), width)]
    raw_data = [r + [''] * (width - len(r)) for r in rows]
    invalid_data = [r + [''] * (width - len(r)) + [line, comments]
                    for r, line, comments in rejected]
    for sheet, names, data in [(raw, raw_headers, raw_data),
                                (bad, raw_headers + ['source_line', 'comments'], invalid_data)]:
        for j, name in enumerate(names, 1):
            sheet.put(f'{column(j)}1', name, style_from='A1')
        for i, values in enumerate(data, 2):
            if sheet is bad:
                sheet.row_attrs[i] = {'r': str(i), 'ht': '34', 'customHeight': '1'}
            for j, value in enumerate(values, 1):
                exemplar = 'I2' if sheet is bad and j == len(names) else 'A2'
                sheet.put(f'{column(j)}{i}', value, style_from=exemplar)
        if not data:
            sheet.put('A2', style_from='A2')
        # Widths also follow additional source columns; comments always get 85 characters.
        cols = sheet.xml.find('s:cols', NS)
        cols.clear()
        for j in range(1, max(21, len(names)) + 1):
            ET.SubElement(cols, f'{{{S}}}col', min=str(j), max=str(j),
                          width='85' if sheet is bad and j == len(names) else '17',
                          customWidth='1', hidden='0')
    metrics, department = [], {}
    for i, obj in enumerate(accepted, 9):
        units, price, cost = int(obj['units']), float(obj['unit_price']), float(obj['unit_cost'])
        revenue, expense = units * price, units * cost
        profit = revenue - expense
        margin = profit / revenue if revenue else 0
        values = [obj[h] for h in REQUIRED]
        values[1] = (date.fromisoformat(obj['date']) - date(1899, 12, 30)).days
        # Excel's historic leap-year bug affects January/February 1900.
        if date.fromisoformat(obj['date']) < date(1900, 3, 1):
            values[1] -= 1
        values[4:7] = [units, price, cost]
        for j, value in enumerate(values, 1):
            p.put(f'{column(j)}{i}', value, style_from=f'{column(j)}9')
        for j, value, formula in [(8, revenue, f'E{i}*F{i}'), (9, expense, f'E{i}*G{i}'),
                                   (10, profit, f'H{i}-I{i}'),
                                   (11, margin, f'IF(H{i}=0,0,J{i}/H{i})')]:
            p.put(f'{column(j)}{i}', value, formula, f'{column(j)}9')
        metrics.append((revenue, expense, profit))
        sums = department.setdefault(obj['department'], [0.0, 0.0])
        sums[0] += revenue
        sums[1] += expense
    end = 8 + len(accepted)
    total_revenue = sum(m[0] for m in metrics)
    total_profit = sum(m[2] for m in metrics)
    p.put('B4', total_revenue, f'SUM(H9:H{end})' if accepted else '0')
    p.put('B5', total_profit, f'SUM(J9:J{end})' if accepted else '0')
    p.put('E4', len(accepted))
    p.put('E5', len(rejected))
    if not accepted:
        p.put('A9', style_from='A9')
    departments = sorted(department)
    for i, dep in enumerate(departments, 9):
        rev, cost = department[dep]
        p.put(f'M{i}', dep, style_from='M9')
        for letter, value, formula in [
            ('N', rev, f'SUMIFS($H$9:$H${end},$C$9:$C${end},M{i})'),
            ('O', cost, f'SUMIFS($I$9:$I${end},$C$9:$C${end},M{i})'),
            ('P', (rev-cost)/100000, f'(N{i}-O{i})/100000'),
            ('Q', rev/total_revenue if total_revenue else 0, f'IF($B$4=0,0,N{i}/$B$4)')]:
            p.put(f'{letter}{i}', value, formula, f'{letter}9')
    for rule in p.xml.findall('s:conditionalFormatting', NS):
        rule.set('sqref', f'J9:K{max(9, end)}')
    # Leave enough room above charts when future files contain many departments.
    shift = max(0, len(departments) - 5)
    if shift:
        drawing_name = 'xl/drawings/drawing1.xml'
        drawing = ET.fromstring(parts[drawing_name])
        for element in drawing.iter():
            if element.tag.endswith('}row'):
                element.text = str(int(element.text) + shift)
        parts[drawing_name] = ET.tostring(drawing, encoding='utf-8', xml_declaration=True)
    for sheet, number in [(p, 1), (raw, 2), (bad, 3)]:
        parts[f'xl/worksheets/sheet{number}.xml'] = sheet.finish()
    specs = {'AcceptedRecords': (REQUIRED + ['Revenue', 'Cost', 'Profit', 'Margin'], 8, len(accepted)),
             'RawRecords': (raw_headers, 1, len(rows)),
             'RejectedRecords': (raw_headers + ['source_line', 'comments'], 1, len(rejected))}
    for name in list(parts):
        if re.fullmatch(r'xl/tables/table\d+\.xml', name):
            table = ET.fromstring(parts[name])
            names, start, count = specs[table.get('name')]
            ref = f'A{start}:{column(len(names))}{start+max(1,count)}'
            table.set('ref', ref)
            table.find('s:autoFilter', NS).set('ref', ref)
            columns = table.find('s:tableColumns', NS)
            columns.clear()
            columns.set('count', str(len(names)))
            for j, heading in enumerate(names, 1):
                ET.SubElement(columns, f'{{{S}}}tableColumn', id=str(j), name=heading)
            parts[name] = ET.tostring(table, encoding='utf-8', xml_declaration=True)
        if re.search(r'/charts/chart\d+\.xml$', name):
            chart = ET.fromstring(parts[name])
            for reference in chart.findall('.//c:strRef', NS) + chart.findall('.//c:numRef', NS):
                formula = reference.find('c:f', NS)
                if formula is None or 'processed' not in formula.text:
                    continue
                letter = re.search(r'\$([A-Z]+)\$9', formula.text)[1]
                formula.text = f"'processed'!${letter}$9:${letter}${8+max(1,len(departments))}"
                cache = reference.find('c:strCache', NS) if letter == 'M' else reference.find('c:numCache', NS)
                for point in list(cache):
                    if point.tag in [f'{{{C}}}pt', f'{{{C}}}ptCount']:
                        cache.remove(point)
                ET.SubElement(cache, f'{{{C}}}ptCount', val=str(len(departments)))
                for j, dep in enumerate(departments):
                    rev, cost = department[dep]
                    value = {'M': dep, 'N': rev, 'O': cost, 'P': (rev-cost)/100000,
                             'Q': rev/total_revenue if total_revenue else 0}[letter]
                    ET.SubElement(ET.SubElement(cache, f'{{{C}}}pt', idx=str(j)), f'{{{C}}}v').text = str(value)
            parts[name] = ET.tostring(chart, encoding='utf-8', xml_declaration=True)
    # Force Excel to refresh formulas after edits; cached results are already populated.
    book = ET.fromstring(parts['xl/workbook.xml'])
    calc = book.find('s:calcPr', NS)
    if calc is None:
        calc = ET.SubElement(book, f'{{{S}}}calcPr')
    calc.attrib.update(calcMode='auto', fullCalcOnLoad='1', forceFullCalc='1')
    parts['xl/workbook.xml'] = ET.tostring(book, encoding='utf-8', xml_declaration=True)
    with ZipFile(target, 'w', ZIP_DEFLATED) as z:
        for name, content in parts.items():
            if name != 'xl/calcChain.xml':
                z.writestr(name, content)
    verify_report(target, len(accepted), len(rejected), total_revenue, total_profit)
    return total_revenue, total_profit


def verify_report(path, accepted, rejected, revenue, profit):
    with ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError('Damaged report ZIP')
        names = [s.get('name') for s in ET.fromstring(z.read('xl/workbook.xml')).find('s:sheets', NS)]
        if names != ['processed', 'raw data', 'invalid sheet']:
            raise ValueError('Unexpected worksheet names')
        charts = [n for n in z.namelist() if re.search(r'/charts/chart\d+\.xml$', n)]
        if len(charts) != 3:
            raise ValueError('Expected three editable charts')
        sheet = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        cells = {c.get('r'): c for c in sheet.findall('.//s:c', NS)}
        for address, expected in [('B4', revenue), ('B5', profit), ('E4', accepted), ('E5', rejected)]:
            if not math.isclose(float(cells[address].find('s:v', NS).text), expected, rel_tol=1e-12):
                raise ValueError('Saved total/count mismatch: ' + address)
        for row in range(9, 9 + accepted):
            for col in 'HIJK':
                if cells[f'{col}{row}'].find('s:f', NS) is None:
                    raise ValueError('Missing calculation formula')
        if sheet.find('.//s:pane', NS) is not None:
            raise ValueError('Unexpected frozen/split panes')
        for name in charts:
            if not ET.fromstring(z.read(name)).findall('.//c:f', NS):
                raise ValueError('Disconnected chart')


def save_record(path, record):
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--template', type=Path, default=Path(__file__).with_name('report_template.xlsx'))
    args = parser.parse_args()
    root = args.root.resolve()
    for folder in ['incoming', 'outgoing', 'archive']:
        (root / folder).mkdir(parents=True, exist_ok=True)
    ledger = root / 'processing_record.json'
    record = json.loads(ledger.read_text(encoding='utf-8-sig')) if ledger.exists() else {'version': 1, 'processed': []}
    # Recover the archive step if an earlier run stopped after recording a verified report.
    for item in record['processed']:
        source = root / 'incoming' / item['source']
        if item.get('status') == 'verified_pending_archive' and source.exists():
            if digest(source.read_bytes()) != item['sha256'] or not Path(item['report']).exists():
                raise ValueError('Pending archive requires review: ' + item['source'])
            destination = root / 'archive' / source.name
            if destination.exists():
                raise FileExistsError('Archive destination already exists: ' + str(destination))
            source.rename(destination)
            item['status'] = 'completed'
            save_record(ledger, record)
    archived = {p.name: digest(p.read_bytes()) for p in (root / 'archive').iterdir()
                if p.is_file() and p.suffix.lower() == '.csv'}
    processed = failed = 0
    for source in sorted((root / 'incoming').iterdir()):
        if not source.is_file() or source.suffix.lower() != '.csv':
            continue
        temporary = None
        try:
            data = source.read_bytes()
            sha = digest(data)
            if source.name in archived or sha in archived.values() or any(
                r.get('source') == source.name or r.get('sha256') == sha for r in record['processed']
            ):
                print('Skipped already processed/archived:', source.name)
                continue
            if not args.template.is_file():
                raise FileNotFoundError('Keep report_template.xlsx beside the script, or use --template')
            target = root / 'outgoing' / (source.stem + '_report.xlsx')
            if target.exists():
                raise FileExistsError('Existing report has no matching processing record; review: ' + str(target))
            destination = root / 'archive' / source.name
            if destination.exists():
                raise FileExistsError('Archive destination already exists')
            headers, rows, accepted, rejected = read_csv(data)
            with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.xlsx', delete=False) as f:
                temporary = Path(f.name)
            revenue, profit = make_report(args.template, temporary, headers, rows, accepted, rejected)
            # Exclusive creation prevents accidental replacement by overlapping invocations.
            with target.open('xb') as f:
                f.write(temporary.read_bytes())
            item = dict(source=source.name, sha256=sha, report=str(target), accepted=len(accepted),
                        rejected=len(rejected), total_revenue=revenue, total_profit=profit,
                        completed_at=datetime.now(timezone.utc).isoformat(), status='verified_pending_archive')
            record['processed'].append(item)
            save_record(ledger, record)
            source.rename(destination)
            item['status'] = 'completed'
            save_record(ledger, record)
            processed += 1
            print(f'{target}: {len(accepted)} accepted, {len(rejected)} rejected; original archived.')
        except Exception as exc:
            failed += 1
            print(f'FAILED {source.name}: {exc}. Input retained unless already archived.')
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    if not processed and not failed:
        print('No new CSVs. No reports recreated.')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
