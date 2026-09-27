"""
app.py — Streamlit front-end for the NL-to-SQL + Report Generator.

Run with:
    streamlit run app.py
"""

import os
import streamlit as st
import pandas as pd

from utils.agent import run_agent
from graphs.charts import auto_chart
from reports.pdf_report import generate_pdf

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NL-to-SQL | Lending Analytics",
    page_icon="🏦",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏦 Lending Analytics")
    st.markdown("Ask anything about the loan database in plain English.")
    st.divider()

    st.subheader("💡 Example Questions")
    examples = [
        "How many loans are active, closed, and defaulted?",
        "What is the average loan amount by loan type?",
        "Which city has the highest number of defaulted loans?",
        "Show total repayments collected per month in 2023",
        "List the top 10 customers by total loan amount",
        "What is the average credit score of customers who defaulted?",
        "How many loans were issued each year?",
        "What percentage of repayments were made on time?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state["question_input"] = ex

    st.divider()
    openai_key = st.text_input("🔑 OpenAI API Key", type="password",
                               help="Enter your OpenAI key. It is never stored.")
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key

# ── Main area ─────────────────────────────────────────────────────────────────
st.markdown("## 🔍 Ask a Question About Your Loan Database")
st.markdown("The AI will generate SQL, run it, visualise the results, and write a summary.")
st.divider()

question = st.text_area(
    "Your question",
    value=st.session_state.get("question_input", ""),
    placeholder="e.g. What is the average loan amount by loan type?",
    height=80,
    label_visibility="collapsed",
)

run_btn = st.button("🚀 Run Analysis", type="primary", use_container_width=False)

# ── Run the agent ─────────────────────────────────────────────────────────────
if run_btn and question.strip():

    if not os.environ.get("OPENAI_API_KEY"):
        st.error("⚠️ Please enter your OpenAI API Key in the sidebar.")
        st.stop()

    with st.spinner("🤖 Agent thinking..."):
        result = run_agent(question)

    error = result.get("error")
    sql   = result.get("sql", "")
    df    = result.get("df")
    summary = result.get("summary", "")

    # ── SQL ───────────────────────────────────────────────────────────────────
    st.markdown("### 🧾 Generated SQL")
    st.code(sql, language="sql")

    if error:
        st.error(f"❌ Query error: {error}")
        st.stop()

    # ── Summary ───────────────────────────────────────────────────────────────
    st.markdown("### 🤖 AI Summary")
    st.info(summary)

    # ── Results table ─────────────────────────────────────────────────────────
    st.markdown(f"### 📋 Results  `{len(df)} rows × {len(df.columns)} columns`")
    st.dataframe(df, use_container_width=True, height=320)

    # ── Chart ─────────────────────────────────────────────────────────────────
    fig = auto_chart(df, question)
    if fig:
        st.markdown("### 📊 Visualisation")
        st.pyplot(fig, use_container_width=True)
    else:
        st.caption("_No chart generated — result set may not be suitable for visualisation._")

    # ── PDF download ──────────────────────────────────────────────────────────
    st.markdown("### 📄 Download Report")
    with st.spinner("Building PDF…"):
        pdf_bytes = generate_pdf(
            question=question,
            sql=sql,
            df=df,
            summary=summary,
            fig=fig,
        )

    st.download_button(
        label="⬇️ Download PDF Report",
        data=pdf_bytes,
        file_name="lending_report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

elif run_btn:
    st.warning("Please enter a question first.")
