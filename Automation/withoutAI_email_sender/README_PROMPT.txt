I gave following prompt to ChatGPT Plus:
-------------------------------------------------------

Role: You are a Python developer writing simple, beginner-friendly automation.

Task: Create an `email_sender` folder with a program that sends personalized Gmail emails using an Excel recipient list.

Requirements:
- Put all editable settings in CAPITAL_LETTER variables at the top: file paths, sender details, column names, and day limit.
- Read a text template containing Subject, From, To, Cc, Name, and Body. Start the body with `Dear {Name},`. Include a sample template.
- Read `faculty_list_for_workshop.xlsx`, using columns `Name`, `Email`, `Date_last_email_sent`, and `To_send_email`. Allow comma-separated email addresses. Leave missing names blank; skip missing emails and rows marked `no`, ignoring case.
- Add a Boolean setting to enable the date check. When enabled, send only if the last-send date is blank or more than a configurable 30 days old.
- Read `GMAIL_APP_PASSWORD` from `.env` without prompting or displaying it.
- Attach every file directly inside an `attachment` folder. Send without attachments if it is missing or empty.
- Print a brief startup summary, then eligible names, addresses, and attachments. Ask for confirmation before sending and stop if declined.
- Print sent/skipped/failed messages. After each successful send, save the current date in that row. Back up Excel first.
- Include dependency and setup files. Check the logic without sending real emails.

What not to do:
Do not hardcode passwords, send without confirmation, update dates for failed sends, change unrelated Excel data, or overcomplicate the code.

-------------------------------------