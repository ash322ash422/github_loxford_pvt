"""
Node 3: apply the university policy to the extracted student info.

Teaching note: for a short policy file like ours, simply stuffing the whole
text into the prompt ("context stuffing") is simpler and more reliable than
RAG. If policy.md grew to many pages, this is the node you'd swap to use a
retriever instead -- the rest of the graph wouldn't need to change.
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

import config
from state import GraphState, PolicyDecision

_llm = ChatOpenAI(model=config.MODEL_NAME, temperature=config.MODEL_TEMPERATURE)
_structured_llm = _llm.with_structured_output(PolicyDecision)

_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You apply a university policy to a student request. You must base "
            "your decision ONLY on the policy text provided -- do not invent "
            "rules that aren't there. If the situation isn't clearly covered, "
            "choose 'escalate_to_professor' rather than guessing.\n\n"
            "POLICY:\n{policy_text}",
        ),
        (
            "human",
            "Email type: {email_type}\n"
            "Student: {student_name} ({roll_number}), course {course_code}\n"
            "Reason given: {reason}\n"
            "Reason category: {reason_category}",
        ),
    ]
)


def apply_policy(state: GraphState) -> GraphState:
    info = state["student_info"]
    chain = _prompt | _structured_llm
    result: PolicyDecision = chain.invoke(
        {
            "policy_text": config.load_policy_text(),
            "email_type": state["classification"].email_type,
            "student_name": info.student_name or "unspecified",
            "roll_number": info.roll_number or "unspecified",
            "course_code": info.course_code or "unspecified",
            "reason": info.reason or "not stated",
            "reason_category": info.reason_category or "unspecified",
        }
    )
    return {
        "policy_decision": result,
        "status": f"policy decision: {result.decision} ({result.rationale})",
    }
