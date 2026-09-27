"""
Entry point. Run with: python main.py

1. Connects to Gmail.
2. Pulls recent unread emails.
3. Runs each one through the LangGraph agent.
4. For relevant emails, writes a draft reply to Gmail Drafts.

The professor still reviews and hits Send -- the agent never sends mail.
"""
import config
import store

from gmail_service import get_gmail_service, fetch_unread_student_emails, create_draft_reply
from graph import student_email_agent
from logger import init_db, log_email_result
init_db()


def process_inbox():
    store.init_db()
    
    
    service = get_gmail_service()
    emails = fetch_unread_student_emails(service, max_results=config.MAX_EMAILS_PER_RUN)
    print(f"Fetched {len(emails)} unread email(s).")

    for email in emails:
        if store.is_already_processed(email["email_id"]):
            print(f"\n--- Skipping '{email['subject']}' (already processed) ---")
            continue

        print(f"\n--- Processing: '{email['subject']}' from {email['sender']} ---")

        final_state = student_email_agent.invoke(
            {
                "email_id": email["email_id"],
                "thread_id": email["thread_id"],
                "sender": email["sender"],
                "subject": email["subject"],
                "body": email["body"],
            }
        )

        print(f"Status: {final_state.get('status')}")

        if final_state.get("is_relevant") and final_state.get("draft_reply"):
            draft = final_state["draft_reply"]
            draft_id = create_draft_reply(
                service,
                thread_id=email["thread_id"],
                to=email["sender"],
                subject=draft.subject,
                body=draft.body,
            )
            log_email_result(final_state, gmail_draft_id=draft_id)
            
            print(f"Draft created (id={draft_id}). Awaiting professor review in Gmail.")
            store.mark_as_processed(
                email_id=email["email_id"],
                subject=email["subject"],
                email_type=final_state["classification"].email_type,
                status=final_state.get("status", ""),
                draft_id=draft_id,
            )   
  
            
        else:
            print("No draft created (not a relevant student-assignment email).")
            store.mark_as_processed(
                email_id=email["email_id"],
                subject=email["subject"],
                email_type=final_state.get("classification").email_type
                if final_state.get("classification")
                else "other",
                status=final_state.get("status", ""),
            )
 


if __name__ == "__main__":
    process_inbox()
