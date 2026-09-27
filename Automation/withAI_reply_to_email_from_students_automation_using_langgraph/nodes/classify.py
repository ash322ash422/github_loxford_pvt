"""
Node 1: classify the incoming email.

Teaching note: this node only looks at subject + a short snippet of the body
because classification is a cheap task and we want to keep it fast/cheap.
Later nodes get the full body when they actually need it.
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

import config
from state import GraphState, EmailClassification

# _llm = ChatOpenAI(model=config.MODEL_NAME, temperature=config.MODEL_TEMPERATURE)
_llm = ChatOpenAI(model=config.MODEL_NAME, temperature=config.MODEL_TEMPERATURE, 
                  api_key=config.OPENAI_API_KEY)
_structured_llm = _llm.with_structured_output(EmailClassification)

_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You triage incoming student emails for a university professor. "
            "Classify the email into exactly one category:\n"
            "- extension_request: asking for more time before a deadline that hasn't passed yet\n"
            "- late_submission: submitting or explaining work that is already past the deadline\n"
            "- grade_clarification: asking about a grade already received\n"
            "- other: anything else (general questions, spam, unrelated topics)",
        ),
        ("human", "Subject: {subject}\n\nBody (first 500 chars):\n{body_snippet}"),
    ]
)


def classify_email(state: GraphState) -> GraphState:
    chain = _prompt | _structured_llm
    result: EmailClassification = chain.invoke(
        {
            "subject": state["subject"],
            "body_snippet": state["body"][:500],
        }
    )
    is_relevant = result.email_type != "other"
    return {
        "classification": result,
        "is_relevant": is_relevant,
        "status": f"classified as '{result.email_type}' ({result.reasoning})",
    }
