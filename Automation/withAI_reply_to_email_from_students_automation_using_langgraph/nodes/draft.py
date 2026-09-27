"""
Node 4: draft the actual reply email, based on the policy decision.
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

import config
from state import GraphState, DraftReply

_llm = ChatOpenAI(model=config.MODEL_NAME, temperature=config.MODEL_TEMPERATURE)
_structured_llm = _llm.with_structured_output(DraftReply)

_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Write a short, polite, professional reply email from a university "
            "department to a student, based on the decision below. "
            "Do not sign it with a specific professor's name -- sign off as "
            "'Course Administration'. Keep it under 150 words. "
            "If the decision is 'escalate_to_professor', do not state any "
            "approval or denial -- just acknowledge receipt and say the "
            "professor will follow up personally.",
        ),
        (
            "human",
            "Student: {student_name}\n"
            "Original subject: {subject}\n"
            "Decision: {decision}\n"
            "Days granted: {days_granted}\n"
            "Requires documentation: {requires_documentation}\n"
            "Rationale: {rationale}",
        ),
    ]
)


def draft_reply(state: GraphState) -> GraphState:
    decision = state["policy_decision"]
    info = state["student_info"]
    chain = _prompt | _structured_llm
    result: DraftReply = chain.invoke(
        {
            "student_name": info.student_name or "Student",
            "subject": state["subject"],
            "decision": decision.decision,
            "days_granted": decision.days_granted or "N/A",
            "requires_documentation": decision.requires_documentation,
            "rationale": decision.rationale,
        }
    )
    return {
        "draft_reply": result,
        "status": "draft written, ready to save to Gmail Drafts",
    }
