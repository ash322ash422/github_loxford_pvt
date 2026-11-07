"""Exercise file movement and send-state handling without WhatsApp or OCR."""
import contextlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app

CFG = json.loads((app.ROOT / 'config.json').read_text())
INVOICE = dict(customer='Test Customer', phone='+12025550123', number='TEST-001',
               date='2026-11-04', amount='100.00')


class ArchiveTests(unittest.TestCase):
    def exercise(self, mode):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, 'ROOT', Path(directory)):
            root = Path(directory)
            path = root / 'invoices/test.pdf'
            path.parent.mkdir()
            path.write_bytes(b'test invoice')
            sender = Mock()
            if mode == 'uncertain':
                sender.sendwhatmsg_instantly.side_effect = RuntimeError('Simulated failure')
            with contextlib.closing(app.database()) as db, \
                 patch.object(app, 'read_invoice', return_value=(INVOICE, 'text')), \
                 patch.dict(sys.modules, {'pywhatkit': sender}), patch.object(app.time, 'sleep'):
                if mode == 'recovery':
                    pending = {}
                    with patch.object(app.shutil, 'move', side_effect=PermissionError('Locked')):
                        self.assertFalse(app.process(path, CFG, db, send=True, pending_moves=pending))
                    self.assertTrue(path.exists())
                    app.process(path, CFG, db, send=True, pending_moves=pending)
                else:
                    if mode == 'collision':
                        (root / 'invoices_processed').mkdir()
                        (root / 'invoices_processed/test.pdf').write_bytes(b'existing invoice')
                    app.process(path, CFG, db, send=mode != 'preview')
                if mode in ('preview', 'uncertain'):
                    self.assertTrue(path.exists())
                    self.assertFalse((root / 'invoices_processed').exists())
                else:
                    self.assertFalse(path.exists())
                    files = list((root / 'invoices_processed').glob('*.pdf'))
                    self.assertIn(b'test invoice', [p.read_bytes() for p in files])
                    if mode == 'collision':
                        self.assertEqual(len(files), 2)
                        self.assertEqual((root / 'invoices_processed/test.pdf').read_bytes(), b'existing invoice')
                self.assertEqual(sender.sendwhatmsg_instantly.call_count, 0 if mode == 'preview' else 1)

    def test_success_moves(self):
        self.exercise('success')

    def test_returned_invoice_sends_again_and_keeps_history(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, 'ROOT', Path(directory)):
            root = Path(directory)
            path = root / 'test.pdf'
            path.write_bytes(b'identical invoice')
            sender = Mock()
            with contextlib.closing(app.database()) as db, \
                 patch.object(app, 'read_invoice', return_value=(INVOICE, 'text')), \
                 patch.dict(sys.modules, {'pywhatkit': sender}), patch.object(app.time, 'sleep'):
                app.process(path, CFG, db, send=True)
                (root / 'invoices_processed/test.pdf').replace(path)
                app.process(path, CFG, db, send=True)
                self.assertEqual(sender.sendwhatmsg_instantly.call_count, 2)
                self.assertEqual(db.execute('SELECT count(*) FROM dispatch').fetchone()[0], 2)
                self.assertEqual(db.execute("SELECT count(*) FROM history WHERE status='archived'").fetchone()[0], 2)

    def test_preview_stays(self):
        self.exercise('preview')

    def test_uncertain_stays(self):
        self.exercise('uncertain')

    def test_collision_preserves_existing_file(self):
        self.exercise('collision')

    def test_move_retry_does_not_resend(self):
        self.exercise('recovery')
