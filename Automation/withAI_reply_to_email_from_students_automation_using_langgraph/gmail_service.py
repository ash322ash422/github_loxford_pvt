"""
Thin wrapper around the Gmail API. Deliberately kept separate from the
LangGraph logic so students can see: "agent brains" (graph.py, nodes/) vs.
"the world the agent acts on" (this file). Swap this file out and the same
graph could run against Outlook, IMAP, a ticketing system, etc.
"""
import base64
from email.mime.text import MIMEText
from typing import List, TypedDict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config


class RawEmail(TypedDict):
    email_id: str
    thread_id: str
    sender: str
    subject: str
    body: str


def _get_credentials() -> Credentials:
    """Load cached OAuth token, refreshing or re-authorizing as needed."""
    creds = None
    if config.GMAIL_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(
            str(config.GMAIL_TOKEN_FILE), config.GMAIL_SCOPES
        )
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(config.GMAIL_CREDENTIALS_FILE), config.GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)
        config.GMAIL_TOKEN_FILE.write_text(creds.to_json())
    return creds


def get_gmail_service():
    creds = _get_credentials()
    return build("gmail", "v1", credentials=creds)


def _extract_body(payload: dict) -> str:
    """Pull the plain-text body out of a Gmail message payload."""
    if payload.get("mimeType") == "text/plain" and "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")

    for part in payload.get("parts", []) or []:
        text = _extract_body(part)
        if text:
            return text
    return ""


def fetch_unread_student_emails(service, max_results: int = 10) -> List[RawEmail]:
    """
    Pull unread inbox emails. In a real deployment you'd likely filter by a
    label (e.g. a Gmail filter that tags student mail as "student-queries")
    so the agent doesn't try to process every unread email in the inbox.
    """
    results = (
        service.users()
        .messages()
        .list(userId="me", labelIds=["INBOX", "UNREAD"], maxResults=max_results)
        .execute()
    )
    message_stubs = results.get("messages", [])

    emails: List[RawEmail] = []
    for stub in message_stubs:
        msg = service.users().messages().get(userId="me", id=stub["id"], format="full").execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        emails.append(
            RawEmail(
                email_id=msg["id"],
                thread_id=msg["threadId"],
                sender=headers.get("From", ""),
                subject=headers.get("Subject", ""),
                body=_extract_body(msg["payload"]),
            )
        )
    return emails


def create_draft_reply(service, thread_id: str, to: str, subject: str, body: str) -> str:
    """
    Writes a reply into Gmail Drafts (does NOT send). Returns the draft ID.
    The professor opens Drafts, reviews, and hits Send themselves.
    """
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    draft = (
        service.users()
        .drafts()
        .create(
            userId="me",
            body={"message": {"raw": raw, "threadId": thread_id}},
        )
        .execute()
    )
    return draft["id"]
