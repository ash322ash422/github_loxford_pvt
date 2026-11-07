# Excel email sender

Requires Python 3.10 or newer. Install Python if needed, then open a terminal in this folder:

```powershell
python -m pip install -r requirements.txt
python send_emails.py
```

To use the existing project virtual environment, run these commands from this folder instead:

```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe send_emails.py
```

## Prepare your files

1. The program uses `faculty_list_for_workshop.xlsx` in this folder. Change `EXCEL_FILE` at the top of `send_emails.py` to use another file. Close it in Excel before running the program.
2. Use these exact headers in row 1 (other columns are allowed):

   | Name | Email | Date_last_email_sent | To_send_email |
   | --- | --- | --- | --- |
   | Alex | alex@example.com | | yes |
   | Sam | sam@example.com, sam.work@example.com | | no |
   | | unnamed@example.com | | yes |
   | No address | | | yes |

3. Edit `email_template.txt`. Keep its header lines and the blank line before the body. The body starts with `Dear {Name},`. A missing name produces `Dear ,` without inventing a name.
4. Set `GOOGLE_EMAIL` and `SENDER_NAME` at the beginning of the script. All user-editable settings are uppercase and grouped there; local working variables inside functions use normal Python naming.

The active Excel sheet is used unless you set `SHEET_NAME`. Headers must be literal text; Name and Email should contain plain values rather than formulas. Supports `.xlsx` and `.xlsm`, not old `.xls` files.

## Template placeholders

- `{Name}`: the current row's Name, or blank when missing.
- `{Email}`: the current row's comma-separated addresses.
- `{From}`: your configured Google email address.
- `{SenderName}`: your configured sender name.

`Name:` is template metadata. It is not sent as an email header. Keep `To: {Email}` so every row goes only to that row's addresses. `Cc:` can remain blank or contain comma-separated email addresses; those people receive a copy of every row's email. All addresses from a row appear together in that message's To field. Different rows receive separate messages.

## Attachments

Place files in the `attachment` folder beside `send_emails.py`. Every email includes all files directly inside that folder, with their original filenames. Subfolders are ignored. A missing or empty folder means emails are sent without attachments. Change `ATTACHMENT_DIRECTORY` at the top of the script to use another folder.

The program lists attachment filenames before confirmation and reads the files once per run so recipients receive the same content. If any file cannot be read, it stops before sending instead of omitting that file.

## Google credentials


This version uses Gmail SMTP with an **app password**, rather than a normal Google password or an OAuth client JSON file. Google requires 2-Step Verification to create app passwords; some organizational accounts or account security settings do not allow them. See [Google's app password instructions](https://support.google.com/mail/answer/185833) and [Google's SMTP documentation](https://developers.google.com/workspace/gmail/imap/imap-smtp).

The script reads the app password from `.env` beside `send_emails.py`; it never prompts for a password. The file must contain a named setting, not just the bare password:

```dotenv
GMAIL_APP_PASSWORD=your_16_character_app_password
```

Use `.env.example` as a format reference. `ENV_FILE` and `APP_PASSWORD_ENVIRONMENT_VARIABLE` at the top of the script control the file location and setting name. An existing environment variable takes precedence over the file. Quotes and Google-style spaces in the password are supported. A missing or blank password stops the program with a setup message before connecting or changing the workbook. `.env` is ignored by Git. The recipient confirmation prompt remains in place. Set `GOOGLE_EMAIL` to the Gmail address that owns this app password.

## Sending and date updates

The program prints skipped rows and every intended To/Cc recipient before asking for confirmation. Anything other than `yes` cancels without sending or changing Excel. Missing addresses are skipped. A row with an invalid address is skipped in full so the problem is visible.

Every fully accepted email updates that row's `Date_last_email_sent` with the computer's local date and time and saves immediately. SMTP acceptance does not guarantee delivery; later bounces are possible. Partial recipient refusals leave the date unchanged and print the rejected addresses. If a connection fails with an uncertain outcome, sending stops. Check Gmail Sent before retrying uncertain or partial sends to avoid duplicates.

Rows with `no` in `To_send_email` are always skipped (ignoring capitalization and surrounding spaces). Blank values and other values allow the other eligibility checks to proceed. The column is required, so a missing header stops the program before sending.

By default, `CHECK_DAYS_SINCE_LAST_EMAIL = True` allows sending only when `Date_last_email_sent` is blank or is **more than 30 calendar days ago**. Exactly 30 days ago, more recent dates, and future dates are skipped. Change `MINIMUM_DAYS_BETWEEN_EMAILS = 30` to change the interval, or set the check to `False` to disable it. Invalid nonblank dates are skipped with an explanation when this check is enabled.

Dates can be Excel date cells, Excel serial dates, ISO dates/timestamps, or text in the formats listed in `TEXT_DATE_FORMATS`. Slash dates are interpreted as day/month/year. Calendar days use the computer's local date. Set `SKIP_PREVIOUSLY_EMAILED = True` to skip all previously emailed rows regardless of age; leave it `False` for the 30-day rule. Duplicate addresses on different rows are treated as separate emails.

A timestamped backup is created before any sending. If a date cannot be saved after a successful send, the program stops and identifies the row that needs manual recording. Do not edit the workbook or run multiple copies while sending.

Other columns and normal formatting are retained. However, openpyxl can lose unsupported Excel objects such as shapes when saving; use a simple recipient workbook and keep the backup. See the [openpyxl workbook documentation](https://openpyxl.readthedocs.io/en/3.1/tutorial.html).

