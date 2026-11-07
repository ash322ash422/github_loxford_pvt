"""First-page invoice notification watcher. Default operation never sends."""
import argparse
import contextlib
import hashlib
import io
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import time
import uuid
from datetime import datetime
from decimal import Decimal

ROOT = Path(__file__).resolve().parent


def extract(text, cfg):
    import phonenumbers
    result = {}
    for field, pattern in cfg['patterns'].items():
        values = re.findall(pattern, text, re.M | re.I)
        if len(values) != 1 or not isinstance(values[0], str) or not values[0].strip():
            raise ValueError(f'{field}: expected exactly one labeled value')
        result[field] = values[0].strip()
    if len(result['customer']) < 2 or not re.search(r'[^\W\d_]', result['customer']):
        raise ValueError('Invalid customer name')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9/_-]{0,63}', result['number']):
        raise ValueError('Invalid invoice number')
    datetime.strptime(result['date'], '%Y-%m-%d')
    raw = result['amount']
    if not re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3})\.\d{2}', raw):
        raise ValueError('Invalid amount grouping')
    amount = Decimal(raw.replace(',', ''))
    if amount <= 0:
        raise ValueError('Amount must be positive')
    result['amount'] = f'{amount:,.2f}'
    if not re.fullmatch(r'\+?[\d ()-]+', result['phone']):
        raise ValueError('Invalid mobile characters')
    phone = phonenumbers.parse(result['phone'], cfg['default_region'])
    if not phonenumbers.is_valid_number(phone):
        raise ValueError('Invalid mobile number')
    result['phone'] = phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)
    return result


def read_invoice(data, cfg, force_ocr=False):
    import pymupdf
    with pymupdf.open(stream=data, filetype='pdf') as doc:
        if doc.needs_pass or not len(doc):
            raise ValueError('Encrypted or empty PDF')
        page = doc[0]
        if not force_ocr:
            logging.info('Reading text from the first PDF page')
            try:
                return extract(page.get_text(sort=True), cfg), 'text'
            except ValueError as exc:
                logging.warning('Text extraction did not validate (%s); trying OCR', exc)
            
        logging.info('Running OCR on the first PDF page')
        import pytesseract
        from PIL import Image
        if cfg.get('tesseract_cmd'):
            pytesseract.pytesseract.tesseract_cmd = cfg['tesseract_cmd']
        pix = page.get_pixmap(dpi=300)
        image = Image.open(io.BytesIO(pix.tobytes('png')))
        words = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config='--psm 6')
        confidence = [float(c) for t, c in zip(words['text'], words['conf']) if t.strip()]
        if not confidence or min(confidence) < cfg['ocr_min_confidence']:
            raise ValueError('OCR confidence too low; review invoice manually')
        text = pytesseract.image_to_string(image, config='--psm 6')
        return extract(text, cfg), 'ocr'


def database():
    (ROOT / 'state').mkdir(exist_ok=True)
    db = sqlite3.connect(ROOT / 'state/invoices.sqlite3')
    db.execute('PRAGMA synchronous=FULL')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS files (
          hash TEXT PRIMARY KEY, filename TEXT, status TEXT, detail TEXT,
          updated TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS dispatch (
          identity TEXT PRIMARY KEY, hash TEXT, status TEXT, detail TEXT,
          updated TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS history (
          id INTEGER PRIMARY KEY AUTOINCREMENT, hash TEXT, filename TEXT,
          status TEXT, detail TEXT, recorded_at TEXT DEFAULT CURRENT_TIMESTAMP);
    ''')
    return db


def record(db, digest, path, status, detail):
    db.execute('INSERT INTO history(hash,filename,status,detail) VALUES(?,?,?,?)',
               (digest, path.name, status, detail))
    db.execute('INSERT OR REPLACE INTO files(hash,filename,status,detail) VALUES(?,?,?,?)',
               (digest, path.name, status, detail))
    db.commit()


def archive_invoice(path, cfg, digest):
    """Move only the bytes that were processed; a failure never enables resending."""
    try:
        folder = Path(cfg.get('processed_folder', 'invoices_processed'))
        if not folder.is_absolute():
            folder = ROOT / folder
        if folder.resolve() == path.parent.resolve():
            raise ValueError('Processed folder must differ from the invoice folder')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('PDF changed during processing; leaving it for review')
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / path.name
        if destination.exists():
            destination = folder / f'{path.stem}_{uuid.uuid4().hex}{path.suffix}'
        shutil.move(str(path), str(destination))
        logging.info('%s: moved to %s', path.name, destination)
        return True
    except (OSError, ValueError, shutil.Error):
        logging.exception('%s: could not move processed invoice; send record retained; will retry moving without resending',
                          path.name)
        return False


def process(path, cfg, db, send=False, force_ocr=False, pending_moves=None):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    pending_moves = pending_moves if pending_moves is not None else {}
    if pending_moves.get(path) == digest:
        moved = archive_invoice(path, cfg, digest)
        if moved:
            record(db, digest, path, 'archived', 'Move retry succeeded; no additional send')
            pending_moves.pop(path, None)
        return moved
    try:
        logging.info('%s: processing invoice', path.name)
        invoice, method = read_invoice(data, cfg, force_ocr)
        logging.info('%s: required fields validated using %s; invoice=%s',
                     path.name, method, invoice['number'])
        message = cfg['message'].format(**invoice, currency=cfg['currency'])
        # Each placement is eligible, including invoices sent in an earlier run.
        identity = uuid.uuid4().hex
        if not send:
            logging.info('%s: PREVIEW ONLY; no message sent; fields=%s; message=%r',
                         path.name, json.dumps(invoice, ensure_ascii=False), message)
            record(db, digest, path, 'preview', method)
            logging.info('%s: preview recorded', path.name)
            return
        # Keep each attempt independently; prior invoices never block this placement.
        db.execute('INSERT INTO dispatch(identity,hash,status) VALUES(?,?,?)', (identity, digest, 'sending'))
        record(db, digest, path, 'sending', json.dumps({'attempt': identity, 'method': method, 'invoice': invoice}))
        logging.info('%s: opening WhatsApp for invoice %s; attempt=%s', path.name, invoice['number'], identity)
        try:
            import pywhatkit
            pywhatkit.sendwhatmsg_instantly(invoice['phone'], message,
                                           wait_time=cfg['wait_time'], tab_close=True, close_time=5)
        except Exception as exc:
            status, detail = 'uncertain', f'{type(exc).__name__}: {exc}'
        else:
            status, detail = 'triggered', 'Browser action returned; delivery is NOT confirmed'
        db.execute('UPDATE dispatch SET status=?,detail=?,updated=CURRENT_TIMESTAMP WHERE identity=?',
                   (status, detail, identity))
        record(db, digest, path, status, detail)
        logging.warning('%s: %s - %s', path.name, status, detail)
        moved = True
        if status == 'triggered':
            pending_moves[path] = digest
            moved = archive_invoice(path, cfg, digest)
            if moved:
                pending_moves.pop(path, None)
            record(db, digest, path, 'archived' if moved else 'move_pending', detail)
        logging.info('Waiting %s seconds before the next invoice', cfg['cooldown_seconds'])
        time.sleep(cfg['cooldown_seconds'])
        return moved
    except Exception as exc:
        # Preserve an already-committed dispatch reservation on ALL failures.
        record(db, digest, path, 'error', f'{type(exc).__name__}: {exc}')
        logging.exception('Invoice rejected: %s', path.name)


@contextlib.contextmanager
def single_instance():
    import msvcrt
    (ROOT / 'state').mkdir(exist_ok=True)
    with open(ROOT / 'state/watcher.lock', 'a+b') as lock:
        lock.seek(0)
        lock.write(b'0')
        lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            logging.error('Another invoice watcher is already running')
            raise SystemExit('Another invoice watcher is already running')
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['watch', 'once', 'status', 'history', 'retry-error'])
    parser.add_argument('--send', action='store_true', help='Enable real WhatsApp browser actions')
    parser.add_argument('--force-ocr', action='store_true')
    parser.add_argument('--hash', help='Exact file hash from status for retry-error')
    args = parser.parse_args()
    (ROOT / 'logs').mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        handlers=[RotatingFileHandler(ROOT / 'logs/app.log', maxBytes=1024,
                                                      backupCount=3, encoding='utf-8'),
                                  logging.StreamHandler(sys.stdout)])
    logging.info('Invoice automation started; command=%s; mode=%s',
                 args.command, 'LIVE SENDING' if args.send else 'PREVIEW')
    cfg = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
    with single_instance(), contextlib.closing(database()) as db:
        if args.command == 'history':
            for row in db.execute('SELECT recorded_at,filename,status,hash,detail FROM history ORDER BY id'):
                logging.info('Recorded_at=%s UTC | file=%s | status=%s | hash=%s | detail=%s', *row)
            return
        if args.command == 'status':
            count = 0
            for row in db.execute('SELECT * FROM files ORDER BY updated DESC'):
                logging.info('File=%s | status=%s | recorded_at=%s UTC | hash=%s | detail=%s',
                             row[1], row[2], row[4], row[0], row[3])
                count += 1
            logging.info('Status complete: %s invoice file(s) recorded', count)
            return
        if args.command == 'retry-error':
            if not args.hash:
                parser.error('--hash is required')
            logging.info('History does not block sending. Restart the watcher to retry files still in invoices. No history deleted.')
            return
        folder = Path(cfg['invoice_folder'])
        if not folder.is_absolute():
            folder = ROOT / folder
        folder.mkdir(parents=True, exist_ok=True)
        logging.info('Watching %s; real sending=%s; Ctrl+C stops', folder, args.send)
        observed = {}
        completed = {}
        pending_moves = {}
        while True:
            present = set(folder.glob('*'))
            for missing in set(observed) - present:
                observed.pop(missing, None)
                completed.pop(missing, None)
                pending_moves.pop(missing, None)
            for path in sorted(folder.glob('*')):
                if path.suffix.lower() != '.pdf' or not path.is_file():
                    continue
                try:
                    st = path.stat()
                    signature = (st.st_size, st.st_mtime_ns, st.st_ctime_ns)
                    previous, since = observed.get(path, (None, time.monotonic()))
                    if previous != signature:
                        observed[path] = (signature, time.monotonic())
                        logging.info('%s: new or changed PDF detected; waiting %s seconds for file stability',
                                     path.name, cfg['stable_seconds'])
                        continue
                    if time.monotonic() - since < cfg['stable_seconds']:
                        continue
                    if completed.get(path) == signature:
                        continue
                    if process(path, cfg, db, args.send, args.force_ocr, pending_moves) is not False:
                        completed[path] = signature
                except OSError:
                    logging.exception('File unavailable: %s; will retry', path.name)
            if args.command == 'once' and observed and all(time.monotonic()-v[1] >= cfg['stable_seconds'] for v in observed.values()):
                logging.info('One-time folder scan complete')
                break
            if args.command == 'once' and not observed:
                logging.info('No invoice PDFs found; one-time folder scan complete')
                break
            time.sleep(cfg['poll_seconds'])


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info('Invoice automation stopped by user')
    except Exception:
        logging.exception('Invoice automation stopped because of an unexpected error')
        raise SystemExit(1)
