"""
Sends the "your tender is ready" email, either through Azure
Communication Services or Gmail SMTP. Both send functions are plain
and side-effecting on purpose - retries/queuing can wrap them later
without changing this module.
"""
import smtplib
from email.message import EmailMessage

from app import config
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

def build_success_email(download_url: str, file_name: str | None = None) -> tuple[str, str]:
    subject = f"Tender Processing Completed: {file_name}"
    body = f"""
            Hello,

            Your tender has been processed successfully.

            You can download the generated Excel file for tender {file_name} using the link below:

            {download_url}

            It is valid for the next {config.URL_EXPIRY_HOURS} hours.

            Regards,
            Tender Automation System
        """
        
    return subject, body


def send_email_through_gmail(to_email: str,
                             subject: str,
                             body: str
) -> None:
    msg = EmailMessage()
    msg["From"] = config.GMAIL_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(config.GMAIL_EMAIL, config.GMAIL_APP_PASSWORD)
        smtp.send_message(msg)

    logger.info("Email sent to %s via Gmail.", to_email)


def send_email_through_azure(recipient: str,
                             subject: str, 
                             body: str
) -> None:
    from azure.communication.email import EmailClient

    client = EmailClient.from_connection_string(config.AZURE_EMAIL_COMMUNICATIONS_STRING)

    message = {
        "senderAddress": config.AZURE_EMAIL_SENDER,
        "recipients": {"to": [{"address": recipient}]},
        "content": {"subject": subject, "plainText": body},
    }

    poller = client.begin_send(message)
    poller.result()
    logger.info("Email sent to %s via Azure Communication Services.", recipient)


def send_notification(recipient: str, 
                      download_url: str,  
                      file_name: str | None = None
) -> None:
    """Picks Azure or Gmail depending on what's configured, Azure first."""
    subject, body = build_success_email(download_url, file_name)

    if config.AZURE_EMAIL_COMMUNICATIONS_STRING and config.AZURE_EMAIL_SENDER:
        send_email_through_azure(recipient, subject, body)
    elif config.GMAIL_EMAIL and config.GMAIL_APP_PASSWORD:
        send_email_through_gmail(recipient, subject, body)
    else:
        raise RuntimeError("No email provider configured (Azure Communication Services or Gmail).")
