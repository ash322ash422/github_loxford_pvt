"""
app.py — Streamlit UI for the NL-to-SQL Multi-Agent System.

Run with:  streamlit run app.py
"""

import os
import streamlit as st
import pandas as pd

from agents.workflow import run_workflow
from graphs.charts import build_chart

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Financial Analytics · Multi-Agent",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Agent badge pills */
.agent-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: .4px;
    margin-bottom: 6px;
}
.badge-analyst  { background:#1a3a5c; color:#4f8ef7; border:1px solid #4f8ef7; }
.badge-reporter { background:#3a1a3a; color:#c084f5; border:1px solid #c084f5; }

/* Metric cards */
.metric-row { display:flex; gap:12px; margin-bottom:8px; }
.metric-card {
    flex:1; background:#1a1f2e; border:1px solid #2a2f3e;
    border-radius:10px; padding:14px 18px;
}
.metric-card .label { font-size:11px; color:#8899bb; margin-bottom:4px; }
.metric-card .value { font-size:22px; font-weight:700; color:#e0e0e0; }
.metric-card .sub   { font-size:10px; color:#556; margin-top:2px; }

/* Pipeline diagram */
.pipeline {
    display:flex; align-items:center; gap:6px;
    padding:10px 16px; background:#10131a;
    border:1px solid #2a2f3e; border-radius:8px;
    font-size:11px; color:#8899bb; flex-wrap:wrap;
}
.pipe-node {
    background:#1a1f2e; border:1px solid #4f8ef7;
    border-radius:6px; padding:4px 10px; color:#4f8ef7;
    font-weight:600; white-space:nowrap;
}
.pipe-node.reporter { border-color:#c084f5; color:#c084f5; }
.pipe-arrow { color:#3a4a5a; font-size:16px; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏦 Financial Analytics")
    st.markdown("**NL-to-SQL · Multi-Agent System**")
    st.divider()

    # API key
    openai_key = st.text_input(
        "🔑 OpenAI API Key",
        type="password",
        placeholder="sk-...",
        help="Never stored. Used only for this session.",
    )
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key

    st.divider()

    # Architecture overview
    st.markdown("#### 🤖 Agent Architecture")
    st.markdown("""
<div style='font-size:12px;color:#8899bb;line-height:1.8'>
<span style='color:#4f8ef7;font-weight:600'>Data Analyst Agent</span><br>
&nbsp;↳ SQL Toolkit<br>
&nbsp;&nbsp;&nbsp;• Schema reader<br>
&nbsp;&nbsp;&nbsp;• Query executor<br>
&nbsp;&nbsp;&nbsp;• Data summariser<br><br>
<span style='color:#c084f5;font-weight:600'>Reporting Agent</span><br>
&nbsp;↳ Visualization Toolkit<br>
&nbsp;&nbsp;&nbsp;• Chart selector<br>
&nbsp;&nbsp;&nbsp;• Narrative writer<br>
&nbsp;↳ PDF Generator<br>
&nbsp;&nbsp;&nbsp;• Full report builder
</div>
""", unsafe_allow_html=True)

    st.divider()

    # Example questions
    st.markdown("#### 💡 Example Questions")
    examples = [
        "How many loans are active, closed, and defaulted?",
        "What is the average loan amount by loan type?",
        "Which city has the most defaulted loans?",
        "Show total repayments collected per month in 2023",
        "Top 10 customers by total loan amount",
        "Average credit score of customers who defaulted vs those who didn't",
        "Distribution of loan interest rates",
        "What percentage of repayments were made on time by loan type?",
        "Monthly transaction volume by category in 2023",
        "Compare average income by city",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True, key=ex):
            st.session_state["q_input"] = ex


# ── Main UI ────────────────────────────────────────────────────────────────────
st.markdown("# 🔍 Financial Analytics · Multi-Agent System")

# Pipeline diagram
st.markdown("""
<div class='pipeline'>
  <span>LangGraph Workflow</span>
  <span class='pipe-arrow'>→</span>
  <span class='pipe-node'>generate_sql</span>
  <span class='pipe-arrow'>→</span>
  <span class='pipe-node'>execute_sql</span>
  <span class='pipe-arrow'>→</span>
  <span class='pipe-node'>data_summary</span>
  <span class='pipe-arrow'>→</span>
  <span class='pipe-node reporter'>choose_chart</span>
  <span class='pipe-arrow'>→</span>
  <span class='pipe-node reporter'>write_narrative</span>
  <span class='pipe-arrow'>→</span>
  <span class='pipe-node reporter'>build_pdf</span>
</div>
""", unsafe_allow_html=True)

st.markdown("")

# Question input
question = st.text_area(
    "Ask a financial question about the lending database",
    value=st.session_state.get("q_input", ""),
    placeholder="e.g.  What is the average loan amount by loan type?",
    height=76,
    label_visibility="collapsed",
)

col_btn1, col_btn2 = st.columns([1, 5])
with col_btn1:
    run_btn = st.button("🚀  Run Agents", type="primary", use_container_width=True)


# ── Execute workflow ───────────────────────────────────────────────────────────
if run_btn and question.strip():

    if not os.environ.get("OPENAI_API_KEY"):
        st.error("⚠️  Please enter your OpenAI API Key in the sidebar.")
        st.stop()

    # Progress through agent nodes
    progress_bar = st.progress(0, text="Starting LangGraph workflow…")
    status_box   = st.empty()

    with st.spinner(""):
        steps = [
            (15,  "🤖 Data Analyst Agent → generating SQL…"),
            (30,  "🛠️  SQL Toolkit → executing query…"),
            (50,  "📊 Data Analyst Agent → summarising results…"),
            (65,  "🎨 Reporting Agent → selecting chart type…"),
            (80,  "✍️  Reporting Agent → writing narrative report…"),
            (95,  "📄 PDF Generator → building report…"),
        ]

        # Fake step display while running
        for pct, msg in steps:
            progress_bar.progress(pct, text=msg)

        result = run_workflow(question)
        progress_bar.progress(100, text="✅  All agents complete.")

    status_box.empty()
    progress_bar.empty()

    error    = result.get("sql_error")
    sql      = result.get("sql", "")
    df       = result.get("df")
    summary  = result.get("data_summary", "")
    narrative = result.get("report_narrative", "")
    chart_type  = result.get("chart_type", "bar")
    chart_title = result.get("chart_title", question[:60])
    pdf_bytes   = result.get("pdf_bytes")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_data, tab_chart, tab_report, tab_pdf = st.tabs([
        "📋  Data & SQL",
        "📊  Visualisation",
        "📝  Report",
        "📄  Download PDF",
    ])

    # ── TAB 1: Data & SQL ─────────────────────────────────────────────────────
    with tab_data:
        st.markdown('<span class="agent-badge badge-analyst">🤖 Data Analyst Agent</span>',
                    unsafe_allow_html=True)

        # Metric cards
        if df is not None and not error:
            cols = st.columns(4)
            with cols[0]:
                st.metric("Rows returned", f"{len(df):,}")
            with cols[1]:
                st.metric("Columns", len(df.columns))
            with cols[2]:
                num_cols = df.select_dtypes("number").columns
                if len(num_cols):
                    col_name = num_cols[0]
                    st.metric(f"Sum of {col_name}", f"{df[col_name].sum():,.0f}")
                else:
                    st.metric("Numeric cols", 0)
            with cols[3]:
                st.metric("Chart type chosen", chart_type.upper())

        # SQL
        st.markdown("#### 🧾 Generated SQL")
        st.markdown('<span class="agent-badge badge-analyst">SQL Toolkit</span>',
                    unsafe_allow_html=True)
        st.code(sql, language="sql")

        if error:
            st.error(f"❌ Query error: {error}")
        else:
            # Summary
            st.markdown("#### 🤖 Data Summary")
            st.info(summary)

            # Table
            st.markdown(f"#### 📋 Results — `{len(df):,}` rows")
            st.dataframe(df, use_container_width=True, height=340)

    # ── TAB 2: Visualisation ──────────────────────────────────────────────────
    with tab_chart:
        st.markdown('<span class="agent-badge badge-reporter">🎨 Reporting Agent · Visualization Toolkit</span>',
                    unsafe_allow_html=True)

        if df is not None and not df.empty and not error:
            # Chart type selector (override)
            chart_opts = ["bar", "line", "scatter", "pie", "histogram"]
            chosen = st.selectbox(
                "Chart type (AI chose — you can override)",
                chart_opts,
                index=chart_opts.index(chart_type) if chart_type in chart_opts else 0,
                key="chart_override",
            )

            fig = build_chart(df=df, chart_type=chosen, title=chart_title)
            if fig:
                st.pyplot(fig, use_container_width=True)
            else:
                st.warning("Could not render chart for this data shape.")

            st.caption(f"**AI-selected chart type:** `{chart_type}` · "
                       f"**Title:** {chart_title}")
        else:
            st.warning("No data available to visualise.")

    # ── TAB 3: Report ─────────────────────────────────────────────────────────
    with tab_report:
        st.markdown('<span class="agent-badge badge-reporter">✍️ Reporting Agent · Narrative Writer</span>',
                    unsafe_allow_html=True)
        st.markdown("#### 📝 Analytical Report")

        if narrative:
            # Styled report card
            paras = [p.strip() for p in narrative.split("\n\n") if p.strip()]
            for para in paras:
                st.markdown(
                    f'<div style="background:#1a1f2e;border-left:3px solid #4f8ef7;'
                    f'padding:12px 16px;border-radius:0 8px 8px 0;'
                    f'margin-bottom:10px;font-size:14px;line-height:1.7;color:#dde2ef">'
                    f'{para}</div>',
                    unsafe_allow_html=True
                )
        else:
            st.warning("No narrative generated.")

    # ── TAB 4: PDF ────────────────────────────────────────────────────────────
    with tab_pdf:
        st.markdown('<span class="agent-badge badge-reporter">📄 PDF Generator</span>',
                    unsafe_allow_html=True)
        st.markdown("#### 📄 Download Full Report")

        if pdf_bytes:
            st.success("✅  PDF report is ready. Click below to download.")

            st.download_button(
                label     = "⬇️  Download PDF Report",
                data      = pdf_bytes,
                file_name = "financial_analytics_report.pdf",
                mime      = "application/pdf",
                use_container_width = True,
            )

            st.markdown("**Report contains:**")
            st.markdown("""
- Question and generated SQL  
- Data Analyst summary  
- Chart / visualisation  
- Full 3-5 paragraph analytical narrative  
- Complete data table (up to 30 rows)  
""")
        else:
            st.warning("No PDF generated — run a query first.")

elif run_btn:
    st.warning("Please type a question first.")

else:
    # Welcome state
    st.markdown("""
    <div style='background:#1a1f2e;border:1px solid #2a2f3e;border-radius:12px;
    padding:28px 32px;margin-top:16px;text-align:center'>
    <div style='font-size:42px;margin-bottom:12px'>🏦</div>
    <div style='font-size:18px;color:#e0e0e0;font-weight:600;margin-bottom:8px'>
        Ask anything about the Finance Database
    </div>
    <div style='font-size:13px;color:#8899bb;line-height:1.7'>
        The <b style='color:#4f8ef7'>Data Analyst Agent</b> will write and execute the SQL.<br>
        The <b style='color:#c084f5'>Reporting Agent</b> will visualise the data and write a full report.<br>
        A <b style='color:#2ecc71'>PDF report</b> is generated automatically for download.
    </div>
    </div>
    """, unsafe_allow_html=True)
