import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app

CFG = json.loads((app.ROOT / 'config.json').read_text())
TEXT = '''Customer Name: Sample Customer
Customer Mobile: +1 202-555-0123
Invoice Number: TEST-2026-001
Invoice Date: 2026-11-04
Invoice Amount: INR 12,500.00
'''


class Tests(unittest.TestCase):
    def test_valid_fields(self):
        result = app.extract(TEXT, CFG)
        self.assertEqual(result['phone'], '+12025550123')
        self.assertEqual(result['amount'], '12,500.00')

    def test_reject_missing_ambiguous_invalid(self):
        for text in [TEXT.replace('Customer Mobile:', 'Seller Mobile:'),
                     TEXT + 'Customer Mobile: +1 202-555-0123\n',
                     TEXT.replace('2026-11-04', '2026-02-30'),
                     TEXT.replace('+1 202-555-0123', '1234'),
                     TEXT.replace('12,500.00', '0.00'),
                     TEXT.replace('12,500.00', '12,50.00')]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                app.extract(text, CFG)

    def test_prior_attempts_do_not_block_new_processing(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, 'ROOT', Path(directory)):
            db = app.database()
            path = Path(directory) / 'a.pdf'
            path.write_bytes(b'fake PDF')
            invoice = app.extract(TEXT, CFG)
            sender = unittest.mock.Mock()
            sender.sendwhatmsg_instantly.side_effect = RuntimeError('simulated UI failure')
            with patch.object(app, 'read_invoice', return_value=(invoice, 'text')), \
                 patch.dict(sys.modules, {'pywhatkit': sender}), patch.object(app.time, 'sleep'):
                app.process(path, CFG, db, send=False)
                sender.sendwhatmsg_instantly.assert_not_called()
                app.process(path, CFG, db, send=True)
                app.process(path, CFG, db, send=True)
                path.write_bytes(b'different PDF same invoice number')
                app.process(path, CFG, db, send=True)
                self.assertEqual(sender.sendwhatmsg_instantly.call_count, 3)
                self.assertEqual(db.execute('SELECT count(*) FROM dispatch').fetchone()[0], 3)
                self.assertEqual(db.execute('SELECT status FROM dispatch').fetchone()[0], 'uncertain')
            db.close()

    def test_sample_first_page(self):
        invoice, method = app.read_invoice((app.ROOT / 'output/pdf/sample_invoice_3_pages.pdf').read_bytes(), CFG)
        self.assertEqual(method, 'text')
        self.assertEqual(invoice['number'], 'TEST-2026-001')


if __name__ == '__main__':
    unittest.main()
