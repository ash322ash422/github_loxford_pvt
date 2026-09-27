"""
Defines:
  1. The Pydantic schemas each LLM node must return (structured output).
  2. The shared GraphState (TypedDict) that flows through every node.

Keeping schemas here (rather than inside each node file) makes it easy to
see, at a glance, everything the agent is capable of "knowing" at each step.
"""
from typing import Literal, Optional, TypedDict
from pydantic import BaseModel, Field


# ---------- Structured outputs the LLM must produce ----------

EmailType = Literal[
    "extension_request",
    "late_submission",
    "grade_clarification",
    "other",
]


class EmailClassification(BaseModel):
    email_type: EmailType = Field(
        description="The single best category for this email."
    )
    reasoning: str = Field(
        description="One short sentence on why this category was chosen."
    )


class StudentInfo(BaseModel):
    student_name: Optional[str] = Field(default=None, description="Student's full name")
    roll_number: Optional[str] = Field(default=None, description="Student roll/ID number")
    course_code: Optional[str] = Field(default=None, description="Course code, e.g. CS301")
    reason: Optional[str] = Field(
        default=None,
        description="The reason the student gave (medical, personal, technical, workload, etc.)",
    )
    reason_category: Optional[
        Literal["medical", "personal_emergency", "technical", "workload", "unspecified"]
    ] = Field(default=None, description="Best-fit bucket for the reason, used to apply policy.")


class PolicyDecision(BaseModel):
    decision: Literal["grant", "partial_grant", "deny", "escalate_to_professor"]
    days_granted: Optional[int] = Field(default=None, description="Extension days granted, if any.")
    requires_documentation: bool = Field(
        default=False, description="Whether the student must supply proof."
    )
    rationale: str = Field(description="Short explanation grounded in the policy text.")


class DraftReply(BaseModel):
    subject: str
    body: str


# ---------- Shared graph state ----------

class GraphState(TypedDict, total=False):
    # input
    email_id: str
    thread_id: str
    sender: str
    subject: str
    body: str

    # produced by nodes
    classification: EmailClassification
    student_info: StudentInfo
    policy_decision: PolicyDecision
    draft_reply: DraftReply

    # bookkeeping
    is_relevant: bool
    status: str  # human-readable trace of what happened, useful for logging/teaching
