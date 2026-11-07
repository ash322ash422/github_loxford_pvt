"""Preview personalized emails, confirm, send through Gmail, and update Excel."""

from pathlib import Path
import mimetypes
import os
import re
import shutil
import smtplib
import ssl
import tempfile
import time
from datetime import date, datetime
from email.message import EmailMessage
from email.parser import Parser

from dotenv import dotenv_values
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel

# EDIT THESE SETTINGS. Relative files are resolved beside this script.
BASE_DIRECTORY = Path(__file__).resolve().parent
TEXT_FILE = BASE_DIRECTORY / "TEST_email_template.txt"
ATTACHMENT_DIRECTORY = BASE_DIRECTORY / "attachment"
EXCEL_FILE = BASE_DIRECTORY / "TEST_faculty_list.xlsx" # Receipients and sent dates are stored here.
SHEET_NAME = None  # None uses the active sheet.
HEADER_ROW = 1
EMAIL_COLUMN = "Email"
NAME_COLUMN = "Name"
DATE_COLUMN = "Date_last_email_sent"
TO_SEND_COLUMN = "To_send_email"
CHECK_DAYS_SINCE_LAST_EMAIL = True  # False disables only the age check.
MINIMUM_DAYS_BETWEEN_EMAILS = 30  # Must be MORE than this many calendar days.
TEXT_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")

GOOGLE_EMAIL = "ash322.ash422@gmail.com"
SENDER_NAME = "Ashwani Kumar"
APP_PASSWORD_ENVIRONMENT_VARIABLE = "GMAIL_APP_PASSWORD"
ENV_FILE = BASE_DIRECTORY / ".env"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_TIMEOUT_SECONDS = 30
SECONDS_BETWEEN_EMAILS = 1
SKIP_PREVIOUSLY_EMAILED = False  # True skips rows with any existing sent date.
DATE_NUMBER_FORMAT = "yyyy-mm-dd"
BACKUP_BEFORE_SENDING = True
ADDRESS_PATTERN = re.compile(r"^[^\s@,;<>]+@[^\s@,;<>]+\.[^\s@,;<>]+$")


def read_app_password():
    """Read the configured secret without displaying it or prompting."""
    settings = dotenv_values(ENV_FILE, encoding="utf-8-sig", interpolate=False)
    password = os.environ.get(APP_PASSWORD_ENVIRONMENT_VARIABLE)
    if password is None:
        password = settings.get(APP_PASSWORD_ENVIRONMENT_VARIABLE)
    password = (password or "").strip().replace(" ", "")
    if not password:
        raise ValueError(
            f"Set {APP_PASSWORD_ENVIRONMENT_VARIABLE} in {ENV_FILE} "
            "or in your environment. No password prompt is used."
        )
    return password


def addresses(value):
    """Accept comma-separated plain email addresses; reject malformed lists."""
    result = []
    for item in str(value or "").split(","):
        address = item.strip()
        if not address:
            continue
        if not ADDRESS_PATTERN.fullmatch(address):
            raise ValueError(f"Invalid email address: {address!r}")
        if address.casefold() not in [entry.casefold() for entry in result]:
            result.append(address)
    return result


def skip_reason(to_send, previous, today, excel_epoch):
    """Return a reason to skip, or None when this row is eligible."""
    if str(to_send or "").strip().casefold() == "no":
        return f"{TO_SEND_COLUMN} is no"
    if previous is None or (isinstance(previous, str) and not previous.strip()):
        return None  # No recorded send: eligible for the first email.
    if SKIP_PREVIOUSLY_EMAILED:
        return "already emailed"
    if not CHECK_DAYS_SINCE_LAST_EMAIL:
        return None
    if isinstance(previous, datetime):
        last_sent = previous.date()
    elif isinstance(previous, date):
        last_sent = previous
    elif isinstance(previous, (int, float)) and not isinstance(previous, bool):
        try:
            last_sent = from_excel(previous, epoch=excel_epoch).date()
        except (ValueError, OverflowError, AttributeError):
            return f"invalid {DATE_COLUMN}; correct it before sending"
    else:
        text = str(previous).strip()
        try:
            last_sent = datetime.fromisoformat(text).date()
        except ValueError:
            for date_format in TEXT_DATE_FORMATS:
                try:
                    last_sent = datetime.strptime(text, date_format).date()
                    break
                except ValueError:
                    continue
            else:
                return f"invalid {DATE_COLUMN}; correct it before sending"
    days = (today - last_sent).days
    if days <= MINIMUM_DAYS_BETWEEN_EMAILS:
        return f"last email date {last_sent}: must be more than {MINIMUM_DAYS_BETWEEN_EMAILS} days ago"
    return None


def read_template():
    template = Parser().parsestr(TEXT_FILE.read_text(encoding="utf-8"))
    for header in ("Subject", "From", "To", "Cc", "Name"):
        if len(template.get_all(header, [])) != 1:
            raise ValueError(f"Template must contain exactly one {header}: header.")
    if not template.get_payload().startswith("Dear {Name}"):
        raise ValueError("Template body must start with Dear {Name}.")
    return template


def read_attachments():
    """Read each direct child file once so every recipient gets the same files."""
    if not ATTACHMENT_DIRECTORY.exists():
        return []
    attachments = []
    for path in sorted(ATTACHMENT_DIRECTORY.iterdir()):
        if path.is_file():
            content_type, encoding = mimetypes.guess_type(path.name)
            if content_type is None or encoding is not None:
                content_type = "application/octet-stream"
            attachments.append((path.name, path.read_bytes(), content_type))
    return attachments


def build_message(template, name, recipients, attachments=()):
    values = {
        "Name": name, "Email": ", ".join(recipients),
        "From": GOOGLE_EMAIL, "SenderName": SENDER_NAME,
    }
    # Only known placeholders are replaced; ordinary braces in text are preserved.
    def render(text):
        return re.sub(r"\{(Name|Email|From|SenderName)\}",
                      lambda match: values[match.group(1)], text)

    message = EmailMessage()
    for header in ("Subject", "From", "To", "Cc"):
        value = render(template[header])
        if value.strip():
            message[header] = value
    if addresses(message.get("To")) != recipients:
        raise ValueError("Template To: must resolve to the row's addresses (use {Email}).")
    if len(addresses(GOOGLE_EMAIL)) != 1:
        raise ValueError("GOOGLE_EMAIL must contain one address.")
    if message["From"].addresses[0].addr_spec != GOOGLE_EMAIL:
        raise ValueError("Template From: must use the configured GOOGLE_EMAIL.")
    cc = addresses(message.get("Cc"))
    message.set_content(render(template.get_payload()))
    for filename, content, content_type in attachments:
        maintype, subtype = content_type.split("/", 1)
        message.add_attachment(content, maintype=maintype, subtype=subtype,
                               filename=filename)
    return message, list(dict.fromkeys(recipients + cc))


def save_workbook(workbook):
    """Replace the workbook only after a complete temporary save."""
    handle, temporary = tempfile.mkstemp(dir=EXCEL_FILE.parent, suffix=EXCEL_FILE.suffix)
    os.close(handle)
    try:
        workbook.save(temporary)
        os.replace(temporary, EXCEL_FILE)
    finally:
        Path(temporary).unlink(missing_ok=True)


def print_startup_summary():
    print("\nEmail sender")
    if SKIP_PREVIOUSLY_EMAILED:
        print(f"Send only when {DATE_COLUMN} is blank (never emailed).")
    elif CHECK_DAYS_SINCE_LAST_EMAIL:
        print(f"Send only when {DATE_COLUMN} is blank or more than "
              f"{MINIMUM_DAYS_BETWEEN_EMAILS} days old.")
    else:
        print("Email age check is disabled; previously emailed rows may be sent again.")
    print(f"Skip rows with no email address or {TO_SEND_COLUMN} = no.")
    print(f"Read recipients: {EXCEL_FILE} (sheet: {SHEET_NAME or 'active sheet'}).")
    print(f"Read message: {TEXT_FILE}.")
    print(f"Attach all files in: {ATTACHMENT_DIRECTORY} (none if missing/empty).")
    print(f"Read Gmail password from {ENV_FILE} or the environment; no password prompt.")
    print(f"Preview recipients, ask for confirmation, then send and update {DATE_COLUMN}.\n")


def run():
    print_startup_summary()

    if MINIMUM_DAYS_BETWEEN_EMAILS < 0:
        raise ValueError("MINIMUM_DAYS_BETWEEN_EMAILS must be nonnegative.")
    
    template = read_template()
    attachments = read_attachments()

    if EXCEL_FILE.suffix.lower() not in (".xlsx", ".xlsm"):
        raise ValueError("Use an .xlsx or .xlsm workbook.")
    workbook = load_workbook(EXCEL_FILE, keep_vba=EXCEL_FILE.suffix.lower() == ".xlsm")
    try:
        sheet = workbook[SHEET_NAME] if SHEET_NAME else workbook.active
        columns = {}
        for cell in sheet[HEADER_ROW]:
            if cell.value is not None:
                label = str(cell.value).strip()
                if label in columns:
                    raise ValueError(f"Duplicate column header: {label}")
                columns[label] = cell.column
        for required in (EMAIL_COLUMN, NAME_COLUMN, DATE_COLUMN, TO_SEND_COLUMN):
            if required not in columns:
                raise ValueError(f"Missing Excel column: {required}")
            
        pending = []
        today = date.today()
        for row in range(HEADER_ROW + 1, sheet.max_row + 1):
            email = sheet.cell(row, columns[EMAIL_COLUMN]).value
            name_value = sheet.cell(row, columns[NAME_COLUMN]).value
            name = "" if name_value is None else str(name_value).strip()
            previous = sheet.cell(row, columns[DATE_COLUMN]).value
            reason = skip_reason(sheet.cell(row, columns[TO_SEND_COLUMN]).value,
                                 previous, today, workbook.epoch)
            if reason:
                print(f"SKIPPED row {row}: {reason} ({name}).")
                continue
            try:
                recipients = addresses(email)
                if not recipients:
                    print(f"SKIPPED row {row}: no email address ({name}).")
                    continue
                message, envelope = build_message(template, name, recipients, attachments)
            except ValueError as error:
                print(f"SKIPPED row {row}: {error}")
                continue
            pending.append((row, name, message, envelope))

        print(f"\nEmails ready to send: {len(pending)}")
        if attachments:
            print("Attachments included in every email:")
            for filename, content, content_type in attachments:
                print(f"  {filename} ({len(content)} bytes)")
        else:
            print("No attachment files found; emails will be sent without attachments.")

        for row, name, message, envelope in pending:
            print(f"  Row {row} | Name: {name} | To: {message['To']} | Cc: {message.get('Cc', '')}")

        if not pending:
            return
        
        if input("\nProceed with sending? Type yes to continue: ").strip().lower() != "yes":
            print("Cancelled. No emails sent; Excel unchanged.")
            return
        
        password = read_app_password()
        if BACKUP_BEFORE_SENDING:
            backup = EXCEL_FILE.with_name(f"{EXCEL_FILE.stem}.backup-{datetime.now():%Y%m%d-%H%M%S-%f}{EXCEL_FILE.suffix}")
            shutil.copy2(EXCEL_FILE, backup)
            print(f"Backup saved: {backup.name}")

        # Check that updates can be saved before sending any email.
        save_workbook(workbook)
        sent = 0
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(GOOGLE_EMAIL, password.replace(" ", ""))
            for row, name, message, envelope in pending:
                print(f"SENDING row {row}: {name} <{message['To']}>")
                try:
                    refused = server.send_message(message, from_addr=GOOGLE_EMAIL, to_addrs=envelope)
                except smtplib.SMTPRecipientsRefused:
                    print(f"FAILED row {row}: all recipients refused; date unchanged.")
                    continue
                except (smtplib.SMTPException, OSError):
                    print(f"STOPPED row {row}: sending failed or outcome uncertain. Check Gmail Sent before retrying.")
                    raise
                if refused:
                    print(f"PARTIAL row {row}: refused addresses: {', '.join(refused)}. Date unchanged; check Gmail before retrying.")
                    continue
                cell = sheet.cell(row, columns[DATE_COLUMN])
                cell.value = datetime.now()
                cell.number_format = DATE_NUMBER_FORMAT
                try:
                    save_workbook(workbook)
                except Exception:
                    print(f"STOPPED: row {row} was sent, but its date could not be saved. Record it manually before retrying.")
                    raise
                sent += 1
                print(f"SENT row {row}: date saved.")
                time.sleep(SECONDS_BETWEEN_EMAILS)

        print(f"Done. {sent} email(s) sent and recorded.")

    finally:
        workbook.close()


if __name__ == "__main__":
    try:
        run()
    except (KeyboardInterrupt, EOFError):
        print("\nStopped by user.")
    except Exception as error:
        print(f"ERROR: {error}")
        raise SystemExit(1)
