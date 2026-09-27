"""
Run the agent on hard-coded sample emails, with NO Gmail setup required.
Shows the full graph trace without needing OAuth credentials. 
This would not create DRAFT emails in Gmail, but it does show what the draft would look like.
If you want to run the agent on real Gmail emails, see main.py instead - That creates DRAFT emails in Gmail, but requires OAuth credentials and a Gmail account.

Run with: python demo.py
"""
from graph import student_email_agent
from student_for_automation_on_emails.logger import init_db, log_email_result
init_db()


SAMPLE_EMAILS = [
    {
        "email_id": "demo-1",
        "thread_id": "demo-thread-1",
        "sender": "priya.sharma@university.edu",
        "subject": "Extension request for Assignment 3",
        "body": (
            """
            Dear Professor, 
            I am Priya Sharma, roll number CS21B045, from course CS301. 
            I was hospitalized for the last two days with a 
            fever and could not finish Assignment 3. Could I please get a "
            short extension?
            
            Thank you,
            Priya
            """
        ),
    },
    {
        "email_id": "demo-2",
        "thread_id": "demo-thread-2",
        "sender": "rahul.verma@university.edu",
        "subject": "Late submission - Assignment 2",
        "body": (
            "Hi, this is Rahul Verma, roll no ME19B012, course ME220. "
            "My laptop crashed the night before the deadline and I lost my "
            "internet for a few hours, so I'm submitting a day late. Sorry "
            "about that."
        ),
    },
    {
        "email_id": "demo-3",
        "thread_id": "demo-thread-3",
        "sender": "ananya.iyer@university.edu",
        "subject": "Question about my midterm grade",
        "body": (
            "Hello, I'm Ananya Iyer (roll EE20B018, course EE305). I got "
            "72/100 on the midterm and I'm not sure why question 4 was marked "
            "wrong. Could someone clarify?"
        ),
    },
    {
        "email_id": "demo-4",
        "thread_id": "demo-thread-4",
        "sender": "someone@university.edu",
        "subject": "Free pizza in the CS lounge today!",
        "body": "Come grab free pizza in the CS lounge from 12-2pm today!",
    },
]


def run_demo():
    for email in SAMPLE_EMAILS:
        print("=" * 70)
        print(f"Subject: {email['subject']}")
        print(f"From:    {email['sender']}")
        print("-" * 70)

        final_state = student_email_agent.invoke(email)

        print(f"Classification : {final_state['classification'].email_type}")
        print(f"Status         : {final_state['status']}")

        if final_state.get("is_relevant"):
            info = final_state["student_info"]
            decision = final_state["policy_decision"]
            draft = final_state["draft_reply"]

            print(f"\nExtracted student info: {info.model_dump()}")
            print(f"\nPolicy decision: {decision.model_dump()}")
            print(f"\n--- DRAFT REPLY ---")
            print(f"Subject: {draft.subject}")
            print(draft.body)
        print()


if __name__ == "__main__":
    run_demo()
