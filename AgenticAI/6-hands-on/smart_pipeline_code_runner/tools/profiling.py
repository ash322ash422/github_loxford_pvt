import csv
import json
import re
from pathlib import Path

ALIASES = {'orderdate': 'order_date', 'date': 'order_date', 'orderid': 'order_id',
           'category': 'category', 'revenue': 'revenue', 'sales': 'revenue'}
REQUIRED = {'order_id', 'order_date', 'category', 'revenue'}


def columns(names):
    return [ALIASES.get(re.sub('[^a-z0-9]', '', n.lower()), n.strip().lower()) for n in names]


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        sample = f.read(8192)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(f, dialect, strict=True)
        header = next(reader)
        return header, list(reader)


def profile_csv(path, relative):
    try:
        header, rows = read_csv(path)
        normalized = columns(header)
        compatible = REQUIRED.issubset(normalized) and len(set(normalized)) == len(normalized)
        return dict(path=relative, columns=header, normalized_columns=normalized,
                    row_count=len(rows), sample_rows=rows[:3], compatible=compatible,
                    missing_cells=sum(not c.strip() for r in rows for c in r),
                    malformed_rows=sum(len(r) != len(header) for r in rows),
                    inferred_types={n: 'text (validated during processing)' for n in normalized})
    except (ValueError, StopIteration, UnicodeError, csv.Error) as e:
        return dict(path=relative, compatible=False, error=str(e))


def read_context_file(path):
    path = Path(path)
    if path.stat().st_size > 2_000_000:
        return {'limitation': 'Context file exceeds 2 MB limit'}
    try:
        if path.suffix.lower() == '.json':
            value = json.loads(path.read_text(encoding='utf-8'))
            return {'valid_json': True, 'excerpt': str(value)[:4000], 'configuration': False}
        if path.suffix.lower() == '.pdf':
            from pypdf import PdfReader
            reader = PdfReader(path)
            text = '\n'.join((p.extract_text() or '')[:2000] for p in reader.pages[:5])[:8000]
            return {'text': text, 'requires_ocr': not text.strip(), 'pages_inspected': min(5, len(reader.pages))}
        text = path.read_text(encoding='utf-8', errors='replace')[:8000]
        return {'excerpt': text, 'error_lines': [l for l in text.splitlines() if 'error' in l.lower()][:20]}
    except Exception as e:
        return {'error': str(e)}
