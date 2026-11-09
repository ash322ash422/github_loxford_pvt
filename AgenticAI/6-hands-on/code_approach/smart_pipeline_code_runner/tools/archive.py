import json
import os
import shutil
from pathlib import Path
from .inventory import digest, safe_path


def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def archive_processed_files(state, archive_root):
    if not state['validation_result']['valid']:
        raise ValueError('Validation required')
    root = Path(archive_root).resolve() / state['run_id']
    journal = Path(state['run_root']) / 'archive_journal.json'
    entries = json.loads(journal.read_text()) if journal.exists() else []
    eligible = set(state['processing_plan']['files'])
    for item in state['file_inventory']:
        if item['path'] not in eligible:
            continue
        source = safe_path(state['input_root'], item['path'])
        target = safe_path(root, item['path'])
        entry = next((e for e in entries if e['path'] == item['path']), None)
        if entry and entry['status'] == 'archived':
            if not target.exists() or digest(target) != item['sha256']:
                raise ValueError('Archived file changed')
            continue
        if not source.exists() and target.exists() and digest(target) == item['sha256']:
            if entry is None:
                raise ValueError('Unjournaled archive destination')
        else:
            if not source.exists() or digest(source) != item['sha256']:
                raise ValueError('Source changed: ' + item['path'])
            if target.exists():
                if entry and entry['status'] == 'pending' and digest(target) == item['sha256']:
                    source.unlink()
                    entry['status'] = 'archived'
                    write_json(journal, entries)
                    continue
                raise ValueError('Archive collision: ' + str(target))
            target.parent.mkdir(parents=True, exist_ok=True)
            entry = dict(path=item['path'], sha256=item['sha256'], destination=str(target), status='pending')
            entries.append(entry)
            write_json(journal, entries)
            # Copy and verify before removing the original. A crash leaves recoverable copies.
            shutil.copyfile(source, target)
            if digest(target) != item['sha256'] or digest(source) != item['sha256']:
                raise ValueError('File changed during archiving')
            source.unlink()
        entry['status'] = 'archived'
        write_json(journal, entries)
    return entries


def restore(run_root, input_root):
    entries = json.loads((Path(run_root) / 'archive_journal.json').read_text())
    for entry in entries:
        source = Path(entry['destination'])
        target = safe_path(input_root, entry['path'])
        if not source.is_file() or digest(source) != entry['sha256']:
            raise ValueError('Archive integrity failure')
        if target.exists():
            if digest(target) == entry['sha256']:
                continue
            raise ValueError('Restore would overwrite a changed file')
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as dest, source.open('rb') as src:
            shutil.copyfileobj(src, dest)
