import os
from typing import Literal

import streamlit as st
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from pypdf import PdfReader


# ---------- Schema ----------
class RubricLevel(BaseModel):
    score: int = Field(description="1 (poor) to 4 (excellent)")
    label: str = Field(description="Short label, e.g. 'Insufficient'")
    descriptor: str = Field(description="Observable behaviour at this level")


class Question(BaseModel):
    question: str
    category: Literal["technical", "behavioral", "situational", "system_design"]
    difficulty: Literal["easy", "medium", "hard"]
    competency: str = Field(description="Skill or competency being assessed")
    good_answer_signals: list[str] = Field(description="2-4 signals of a strong answer")
    red_flags: list[str] = Field(description="1-3 warning signs")
    rubric: list[RubricLevel] = Field(description="Exactly 4 levels, scores 1-4")


class InterviewKit(BaseModel):
    role: str
    questions: list[Question]


# ---------- Providers ----------
PROVIDERS = {
    "OpenAI": {"model": "gpt-4o-mini", "env": "OPENAI_API_KEY"},
    "Groq": {"model": "llama-3.3-70b-versatile", "env": "GROQ_API_KEY"},
    "Gemini": {"model": "gemini-2.5-flash", "env": "GOOGLE_API_KEY"},
}


def build_llm(provider: str, model: str, api_key: str, temperature: float):
    if provider == "OpenAI":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, api_key=api_key, temperature=temperature)
    if provider == "Groq":
        from langchain_groq import ChatGroq

        return ChatGroq(model=model, api_key=api_key, temperature=temperature)
    if provider == "Gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model, google_api_key=api_key, temperature=temperature
        )
    raise ValueError(f"Unknown provider: {provider}")


# ---------- Prompt ----------
PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert technical recruiter and interview designer. "
            "Generate role-specific interview questions with scoring rubrics. "
            "Questions must be concrete, non-generic, and calibrated to the seniority level. "
            "Each rubric has exactly 4 levels (scores 1-4) with observable, distinct descriptors.",
        ),
        (
            "human",
            "Role: {role}\n"
            "Seniority: {seniority}\n"
            "Key skills: {skills}\n"
            "Question categories: {categories}\n"
            "Number of questions: {n}\n"
            "Job description (optional):\n{jd}\n\n"
            "Generate the interview kit.",
        ),
    ]
)


def generate(llm, **inputs) -> InterviewKit:
    chain = PROMPT | llm.with_structured_output(InterviewKit)
    return chain.invoke(inputs)


def read_pdf(file) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(file).pages)


def to_markdown(kit: InterviewKit) -> str:
    out = [f"# Interview Kit: {kit.role}\n"]
    for i, q in enumerate(kit.questions, 1):
        out.append(f"## Q{i}. {q.question}")
        out.append(f"*{q.category} | {q.difficulty} | {q.competency}*\n")
        out.append("**Good answer signals**")
        out += [f"- {s}" for s in q.good_answer_signals]
        out.append("\n**Red flags**")
        out += [f"- {s}" for s in q.red_flags]
        out.append("\n**Rubric**\n\n| Score | Label | Descriptor |\n|---|---|---|")
        out += [f"| {r.score} | {r.label} | {r.descriptor} |" for r in sorted(q.rubric, key=lambda r: r.score)]
        out.append("")
    return "\n".join(out)


# ---------- UI ----------
st.set_page_config(page_title="Interview Question Generator", layout="wide")
st.title("AI Interview Question & Rubric Generator")

with st.sidebar:
    st.header("Model")
    provider = st.selectbox("Provider", list(PROVIDERS))
    cfg = PROVIDERS[provider]
    model = st.text_input("Model name", value=cfg["model"], key=f"model_{provider}")
    api_key = st.text_input(
        "API key",
        type="password",
        value=os.getenv(cfg["env"], ""),
        key=f"key_{provider}",
        help=f"Falls back to {cfg['env']} env var.",
    )
    temperature = st.slider("Temperature", 0.0, 1.0, 0.4, 0.1)

col1, col2 = st.columns(2)
with col1:
    role = st.text_input("Role", placeholder="e.g. Senior Data Engineer")
    seniority = st.selectbox("Seniority", ["Intern", "Junior", "Mid", "Senior", "Lead/Staff"], index=2)
    skills = st.text_input("Key skills (comma-separated)", placeholder="Python, Spark, Airflow, SQL")
with col2:
    categories = st.multiselect(
        "Categories",
        ["technical", "behavioral", "situational", "system_design"],
        default=["technical", "behavioral"],
    )
    n = st.slider("Number of questions", 3, 15, 6)
    jd_file = st.file_uploader("Job description (PDF, optional)", type="pdf")

jd_text = st.text_area("Or paste job description (optional)", height=120)
if jd_file:
    jd_text = read_pdf(jd_file)

if st.button("Generate", type="primary"):
    if not role or not api_key or not categories:
        st.error("Role, API key, and at least one category are required.")
    else:
        try:
            with st.spinner(f"Generating with {provider}..."):
                llm = build_llm(provider, model, api_key, temperature)
                st.session_state.kit = generate(
                    llm,
                    role=role,
                    seniority=seniority,
                    skills=skills or "not specified",
                    categories=", ".join(categories),
                    n=n,
                    jd=jd_text[:8000] or "not provided",
                )
        except Exception as e:
            st.error(f"{type(e).__name__}: {e}")

kit: InterviewKit | None = st.session_state.get("kit")
if kit:
    st.subheader(f"Interview kit: {kit.role}")
    for i, q in enumerate(kit.questions, 1):
        with st.expander(f"Q{i}. {q.question}", expanded=(i == 1)):
            st.caption(f"{q.category} | {q.difficulty} | {q.competency}")
            a, b = st.columns(2)
            a.markdown("**Good answer signals**\n" + "\n".join(f"- {s}" for s in q.good_answer_signals))
            b.markdown("**Red flags**\n" + "\n".join(f"- {s}" for s in q.red_flags))
            st.table(
                [
                    {"Score": r.score, "Label": r.label, "Descriptor": r.descriptor}
                    for r in sorted(q.rubric, key=lambda r: r.score)
                ]
            )
    d1, d2 = st.columns(2)
    d1.download_button("Download Markdown", to_markdown(kit), "interview_kit.md")
    d2.download_button("Download JSON", kit.model_dump_json(indent=2), "interview_kit.json")
