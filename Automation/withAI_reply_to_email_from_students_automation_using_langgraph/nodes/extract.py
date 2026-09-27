"""
Node 2: extract structured student info from the full email body.
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

import config
from state import GraphState, StudentInfo

_llm = ChatOpenAI(model=config.MODEL_NAME, temperature=config.MODEL_TEMPERATURE)
_structured_llm = _llm.with_structured_output(StudentInfo)

_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Extract the student's details from this email. If a field isn't "
            "mentioned, leave it null rather than guessing. For reason_category, "
            "pick the closest bucket based on what the student actually wrote.",
        ),
        (
            "human",
            "Sender: {sender}\nSubject: {subject}\n\nBody:\n{body}",
        ),
    ]
)


def extract_student_info(state: GraphState) -> GraphState:
    chain = _prompt | _structured_llm
    result: StudentInfo = chain.invoke(
        {
            "sender": state["sender"],
            "subject": state["subject"],
            "body": state["body"],
        }
    )
    return {
        "student_info": result,
        "status": f"extracted info for {result.student_name or 'unknown student'}",
    }
