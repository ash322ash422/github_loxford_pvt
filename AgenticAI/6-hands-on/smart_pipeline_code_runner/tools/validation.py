import csv
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from .profiling import read_csv, columns


def validate_outputs(run_root, plan):
    root = Path(run_root)
    try:
        def load(name, fields):
            path = root / 'outputs' / name
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 16_777_216:
                raise ValueError('Invalid output file: ' + name)
            with path.open(encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                if reader.fieldnames != fields:
                    raise ValueError('Unexpected schema: ' + name)
                return list(reader)
        master = load('master_data.csv', ['order_id', 'order_date', 'category', 'revenue', 'source_file', 'source_row', 'original_values'])
        rejected = load('rejected_rows.csv', ['source_file', 'source_row', 'reason', 'original_values'])
        summary = load('summary.csv', ['month', 'category', 'revenue', 'order_count'])
        expected, invalid, seen, source_count = {}, {}, set(), 0
        for name in plan['files']:
            header, rows = read_csv(root / 'inputs' / name)
            keys = columns(header)
            for n, values in enumerate(rows, 2):
                source_count += 1
                row = dict(zip(keys, values))
                key = (name, str(n))
                try:
                    assert len(values) == len(header)
                    order, category = row['order_id'].strip(), row['category'].strip()
                    assert order and category
                    day = date.fromisoformat(row['order_date'].strip()).isoformat()
                    amount = Decimal(row['revenue'].strip())
                    assert amount.is_finite() and amount >= 0 and amount == amount.quantize(Decimal('.01'))
                except Exception:
                    invalid[key] = 'invalid'
                    continue
                if order in seen:
                    invalid[key] = 'duplicate'
                    continue
                seen.add(order)
                expected[key] = (order, day, category, amount, dict(zip(header, values)))
        actual = {}
        totals = defaultdict(lambda: [Decimal(0), 0])
        for row in master:
            key = (row['source_file'], row['source_row'])
            if key in actual:
                raise ValueError('Duplicate provenance')
            actual[key] = (row['order_id'], row['order_date'], row['category'], Decimal(row['revenue']), json.loads(row['original_values']))
            group = (row['order_date'][:7], row['category'])
            totals[group][0] += Decimal(row['revenue'])
            totals[group][1] += 1
        if actual != expected:
            raise ValueError('Accepted records do not match independent source calculation')
        if Counter((r['source_file'], r['source_row']) for r in rejected) != Counter(invalid.keys()):
            raise ValueError('Rejected row reconciliation failed')
        for r in rejected:
            if not r['reason'] or (invalid[(r['source_file'], r['source_row'])] == 'duplicate' and r['reason'] != 'duplicate_order_id'):
                raise ValueError('Invalid rejection reason')
        computed = {(r['month'], r['category']): [Decimal(r['revenue']), int(r['order_count'])] for r in summary}
        if len(computed) != len(summary) or computed != dict(totals):
            raise ValueError('Summary reconciliation failed')
        return dict(valid=True, source_rows=source_count, accepted=len(master), rejected=len(rejected),
                    duplicates=list(invalid.values()).count('duplicate'),
                    revenue=str(sum((v[3] for v in expected.values()), Decimal(0))))
    except Exception as e:
        return {'valid': False, 'error': str(e)}
