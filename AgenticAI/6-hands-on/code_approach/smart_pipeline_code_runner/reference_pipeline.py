"""Offline fixture and documented processing contract; uses only the standard library."""
import csv
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


def process(input_root, output_root, plan):
    out = Path(output_root)
    out.mkdir(exist_ok=True, parents=True)
    accepted, rejected, seen, totals = [], [], set(), {}
    import re
    aliases = {'orderdate': 'order_date', 'date': 'order_date', 'orderid': 'order_id',
               'category': 'category', 'revenue': 'revenue', 'sales': 'revenue'}
    for name in plan['files']:
        with (Path(input_root) / name).open(encoding='utf-8-sig', newline='') as f:
            sample = f.read(8192)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
            except csv.Error:
                dialect = csv.excel
            reader = csv.reader(f, dialect, strict=True)
            header = next(reader)
            keys = [aliases.get(re.sub('[^a-z0-9]', '', h.lower()), h.strip().lower()) for h in header]
            for number, values in enumerate(reader, 2):
                raw = json.dumps(dict(zip(header, values)), ensure_ascii=False)
                reason = ''
                row = dict(zip(keys, values))
                try:
                    if len(values) != len(header):
                        raise ValueError('column_count')
                    order = row['order_id'].strip()
                    category = row['category'].strip()
                    if not order or not category:
                        raise ValueError('missing_required_value')
                    day = date.fromisoformat(row['order_date'].strip()).isoformat()
                    revenue = Decimal(row['revenue'].strip())
                    if not revenue.is_finite() or revenue < 0 or revenue != revenue.quantize(Decimal('.01')):
                        raise ValueError('invalid_revenue')
                    if order in seen:
                        raise ValueError('duplicate_order_id')
                except (ValueError, InvalidOperation, KeyError) as e:
                    reason = str(e) or 'invalid_value'
                if reason:
                    rejected.append([name, number, reason, raw])
                    continue
                seen.add(order)
                accepted.append([order, day, category, str(revenue), name, number, raw])
                key = (day[:7], category)
                amount, count = totals.get(key, (Decimal(0), 0))
                totals[key] = (amount + revenue, count + 1)
    def write(name, header, rows):
        with (out / name).open('w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
    write('master_data.csv', ['order_id', 'order_date', 'category', 'revenue', 'source_file', 'source_row', 'original_values'], accepted)
    write('rejected_rows.csv', ['source_file', 'source_row', 'reason', 'original_values'], rejected)
    write('summary.csv', ['month', 'category', 'revenue', 'order_count'],
          [[*key, str(value[0]), value[1]] for key, value in sorted(totals.items())])


if __name__ == '__main__':
    import sys
    process(sys.argv[1], sys.argv[2], json.loads(Path(sys.argv[3]).read_text()))
