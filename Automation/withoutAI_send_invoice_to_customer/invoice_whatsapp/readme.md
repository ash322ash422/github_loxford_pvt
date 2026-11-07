# Invoice WhatsApp automation

Reads page 1 of invoice PDFs, prepares a WhatsApp text message, and moves sent invoices to `invoices_processed`. Only PDFs are processed; `.docx` files are ignored.

## Install

Requires Windows and Python 3.11+. Open a terminal in this directory:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

For scanned PDFs, install Tesseract OCR with English language data and set `tesseract_cmd` in `config.json`. Edit the field `patterns` to match your invoices, and check the `message`, phone region, currency, and folder settings.

## Run

Put completed invoice PDFs in `invoices`.

Preview continuously without sending or moving files:

```powershell
.venv\Scripts\python.exe app.py watch
```

Preview the current folder once and exit:

```powershell
.venv\Scripts\python.exe app.py once
```

**Send option:** add `--send` to enable real WhatsApp messages:

```powershell
.venv\Scripts\python.exe app.py watch --send
```

For a single scan with sending, use `app.py once --send`. Stop continuous monitoring with **Ctrl+C**. Add `--force-ocr` to either scan command to use OCR instead of PDF text extraction.

Before sending, sign into WhatsApp Web in your default browser. Keep the PC awake, unlocked, and connected to the internet. Verify extraction in preview mode first.

- Every valid PDF in `invoices` is eligible, even if sent before. Returning a processed PDF to this folder requests another send.
- After the send action completes, the PDF moves to `invoices_processed`. Existing files there are preserved with a unique suffix when names collide.
- Missing/invalid fields and uncertain sends are logged; those files stay in `invoices`.
- A failed move is retried without resending during the same run. Restarting attempts all PDFs still in `invoices` again.
- Pywhatkit cannot confirm delivery. The application sends the text message, not the PDF attachment.

## Logs and history

Timestamped `INFO`, `WARNING`, and `ERROR` messages appear in the console and `logs/app.log`. Open that file in a text editor to view recent activity. It rotates at approximately **1 KB**, keeping three backups: `app.log.1` through `app.log.3`. A long message can exceed 1 KB.

Latest status per file hash:

```powershell
.venv\Scripts\python.exe app.py status
```

Full processing history, including repeat sends:

```powershell
.venv\Scripts\python.exe app.py history
```

History is retained separately in `state/invoices.sqlite3` and is not removed by log rotation. Stop the watcher before running status/history commands. To retry an error after fixing configuration, restart the watcher; clearing history is unnecessary.

## Tests

Run the file movement and repeat-sending tests (no real messages):

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_archiving.py -v
```

Run all tests:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The full suite expects `output/pdf/sample_invoice_3_pages.pdf`. That location is currently absent; the sample PDF is in `invoices_processed`. Copy it to the expected test location before running the full suite. Keep sample invoices out of `invoices` when using `--send`.
