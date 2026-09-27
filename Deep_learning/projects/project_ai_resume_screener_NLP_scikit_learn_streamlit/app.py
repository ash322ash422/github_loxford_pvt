"""
app.py — AI Resume Screening System
Streamlit UI entry point.
"""

import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from parser import parse_resume, parse_job_description
from skill_matcher import batch_skill_scores
from semantic_ranker import batch_semantic_scores
from recommender import rank_candidates, summarise_ranking

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Resume Screener",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #6366f1, #8b5cf6, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #6b7280;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #f0f4ff, #e8eaff);
        border-radius: 12px;
        padding: 1.2rem;
        border-left: 4px solid #6366f1;
    }
    .candidate-card {
        background: #fafafa;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        border: 1px solid #e5e7eb;
    }
    .rank-badge {
        background: #6366f1;
        color: white;
        border-radius: 50%;
        width: 32px;
        height: 32px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.9rem;
    }
    .skill-chip {
        display: inline-block;
        background: #dcfce7;
        color: #166534;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.78rem;
        margin: 2px;
    }
    .missing-chip {
        display: inline-block;
        background: #fee2e2;
        color: #991b1b;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.78rem;
        margin: 2px;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #e5e7eb;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
SAMPLE_JD = """Senior Machine Learning Engineer

We are looking for an experienced Machine Learning Engineer to join our AI team.

Requirements:
- 4+ years of experience in machine learning and deep learning
- Strong proficiency in Python, TensorFlow, PyTorch
- Experience with NLP techniques including BERT, Transformers, Huggingface
- Knowledge of scikit-learn, pandas, numpy
- Experience deploying models on AWS or GCP using Docker and Kubernetes
- Familiarity with SQL and NoSQL databases (PostgreSQL, MongoDB)
- Understanding of CI/CD pipelines and Git
- Experience with Apache Spark or Airflow is a plus
"""


def load_sample_resumes() -> list[tuple[str, str]]:
    """Return [(filename, text), ...] from sample_resumes/."""
    folder = os.path.join(os.path.dirname(__file__), "sample_resumes")
    samples = []
    if os.path.isdir(folder):
        for fname in sorted(os.listdir(folder)):
            if fname.endswith(".txt"):
                with open(os.path.join(folder, fname), "r", encoding="utf-8") as f:
                    samples.append((fname, f.read()))
    return samples


@st.cache_resource(show_spinner=False)
def warm_up_model():
    """Pre-load the sentence-transformer model once."""
    from semantic_ranker import _get_model
    return _get_model()


def score_gauge(score: float, title: str = "") -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "%", "font": {"size": 28}},
        title={"text": title, "font": {"size": 13}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": "#6366f1"},
            "steps": [
                {"range": [0, 40],  "color": "#fee2e2"},
                {"range": [40, 60], "color": "#fef3c7"},
                {"range": [60, 80], "color": "#dcfce7"},
                {"range": [80, 100],"color": "#d1fae5"},
            ],
            "threshold": {
                "line": {"color": "#6366f1", "width": 3},
                "thickness": 0.75,
                "value": score,
            },
        },
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=30, b=10))
    return fig


def skills_bar_chart(candidates: list[dict]) -> go.Figure:
    names  = [c["name"] for c in candidates]
    skill  = [c["skill_score"] for c in candidates]
    sem    = [c["semantic_score"] for c in candidates]
    final  = [c["final_score"] for c in candidates]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Skill Match",     x=names, y=skill,  marker_color="#6366f1"))
    fig.add_trace(go.Bar(name="Semantic Match",  x=names, y=sem,    marker_color="#8b5cf6"))
    fig.add_trace(go.Bar(name="Final Score",     x=names, y=final,  marker_color="#a78bfa"))

    fig.update_layout(
        barmode="group",
        title="Score Breakdown by Candidate",
        yaxis_title="Score (%)",
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=380,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def skill_coverage_radar(candidate: dict, jd_skills: list[str]) -> go.Figure:
    if not jd_skills:
        return None
    matched_set = set(candidate.get("matched_skills", []))
    vals = [1 if s in matched_set else 0 for s in jd_skills]
    vals += [vals[0]]  # close the polygon
    cats = jd_skills + [jd_skills[0]]

    fig = go.Figure(go.Scatterpolar(
        r=vals, theta=cats, fill="toself",
        line_color="#6366f1", fillcolor="rgba(99,102,241,0.2)"
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=False, range=[0, 1])),
        showlegend=False,
        height=300,
        margin=dict(l=30, r=30, t=30, b=30),
    )
    return fig


# ── App Layout ────────────────────────────────────────────────────────────────
def main():
    # Header
    st.markdown('<p class="main-header">🤖 AI Resume Screening System</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">NLP + Deep Learning powered candidate ranking • Skill matching • Semantic analysis</p>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        skill_weight = st.slider("Skill Match Weight", 0.1, 0.9, 0.4, 0.05,
                                  help="Weight given to keyword skill matching")
        semantic_weight = round(1.0 - skill_weight, 2)
        st.caption(f"Semantic Weight: **{semantic_weight}**")
        st.markdown("---")
        st.caption("Model: `all-MiniLM-L6-v2`")
        st.caption("NLP: spaCy + NLTK")
        st.caption("Skill vocab: 80+ tech skills")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📋 Input & Screen", "📊 Analysis", "📄 Candidate Details"])

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 1 — Input
    # ─────────────────────────────────────────────────────────────────────────
    with tab1:
        col_jd, col_res = st.columns([1, 1], gap="large")

        with col_jd:
            st.subheader("📝 Job Description")
            use_sample_jd = st.toggle("Use sample JD", value=True)
            jd_text = st.text_area(
                "Paste job description here",
                value=SAMPLE_JD if use_sample_jd else "",
                height=320,
                label_visibility="collapsed",
            )

        with col_res:
            st.subheader("📂 Resumes")
            input_mode = st.radio(
                "Input mode",
                ["Load sample resumes", "Paste resume text", "Upload .txt files"],
                horizontal=True,
            )

            resume_entries: list[tuple[str, str]] = []   # [(label, text)]

            if input_mode == "Load sample resumes":
                samples = load_sample_resumes()
                if samples:
                    st.success(f"✅ {len(samples)} sample resumes loaded")
                    for fname, _ in samples:
                        st.caption(f"• {fname}")
                    resume_entries = samples
                else:
                    st.warning("No sample resumes found in `sample_resumes/` folder.")

            elif input_mode == "Paste resume text":
                n = st.number_input("Number of resumes", 1, 10, 2)
                for i in range(int(n)):
                    with st.expander(f"Resume {i+1}", expanded=(i == 0)):
                        txt = st.text_area(f"Resume {i+1} text", height=200, key=f"res_{i}", label_visibility="collapsed")
                        if txt.strip():
                            resume_entries.append((f"Resume {i+1}", txt))

            else:
                uploaded = st.file_uploader("Upload .txt resume files", type=["txt"], accept_multiple_files=True)
                for uf in uploaded:
                    resume_entries.append((uf.name, uf.read().decode("utf-8", errors="ignore")))

        st.markdown("---")
        run_btn = st.button("🚀 Screen Candidates", type="primary", use_container_width=True)

        if run_btn:
            if not jd_text.strip():
                st.error("Please enter a job description.")
                return
            if not resume_entries:
                st.error("Please provide at least one resume.")
                return

            # ── Pipeline ──────────────────────────────────────────────────
            with st.status("Running AI screening pipeline...", expanded=True) as status:
                st.write("📖 Parsing resumes and job description…")
                jd_parsed = parse_job_description(jd_text)
                candidates = []
                for label, text in resume_entries:
                    parsed = parse_resume(text)
                    parsed["label"] = label
                    candidates.append(parsed)

                st.write("🔤 Extracting & matching skills (TF-IDF)…")
                candidates = batch_skill_scores(candidates, jd_text)

                st.write("🧠 Computing semantic similarity (BERT embeddings)…")
                candidates = batch_semantic_scores(candidates, jd_text)

                st.write("🏆 Ranking candidates…")
                ranked = rank_candidates(candidates, jd_parsed)
                summary = summarise_ranking(ranked)
                status.update(label="✅ Screening complete!", state="complete")

            st.session_state["ranked"]     = ranked
            st.session_state["summary"]    = summary
            st.session_state["jd_parsed"]  = jd_parsed
            st.session_state["jd_text"]    = jd_text

            # Quick result preview
            st.success(f"Screened **{summary['total']}** candidates | Top score: **{summary['top_score']}%** | Avg: **{summary['avg_score']}%**")

            st.markdown("### 🏅 Quick Rankings")
            for c in ranked:
                cols = st.columns([0.08, 0.3, 0.15, 0.15, 0.15, 0.17])
                cols[0].markdown(f"**#{c['rank']}**")
                cols[1].markdown(f"**{c['name']}**")
                cols[2].metric("Skill", f"{c['skill_score']}%")
                cols[3].metric("Semantic", f"{c['semantic_score']}%")
                cols[4].metric("Final", f"{c['final_score']}%")
                cols[5].markdown(c["recommendation"])

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 2 — Analysis
    # ─────────────────────────────────────────────────────────────────────────
    with tab2:
        if "ranked" not in st.session_state:
            st.info("Run the screening pipeline first (Tab 1).")
            return

        ranked  = st.session_state["ranked"]
        summary = st.session_state["summary"]

        # Summary metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Candidates", summary["total"])
        m2.metric("Top Score",        f"{summary['top_score']}%")
        m3.metric("Average Score",    f"{summary['avg_score']}%")
        m4.metric("🟢 Highly Rec.",   summary["highly_recommended"])
        m5.metric("🟡 Recommended",   summary["recommended"])

        st.plotly_chart(skills_bar_chart(ranked), use_container_width=True)

        # Final score distribution
        fig_hist = px.histogram(
            x=[c["final_score"] for c in ranked],
            nbins=10,
            title="Final Score Distribution",
            labels={"x": "Score (%)"},
            color_discrete_sequence=["#6366f1"],
        )
        fig_hist.update_layout(
            plot_bgcolor="white", height=280,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        col_hist, col_pie = st.columns(2)
        with col_hist:
            st.plotly_chart(fig_hist, use_container_width=True)

        with col_pie:
            labels = ["🟢 Highly Rec", "🟡 Recommended", "🟠 Consider", "🔴 Not Rec"]
            values = [
                summary["highly_recommended"],
                summary["recommended"],
                summary["consider"],
                summary["not_recommended"],
            ]
            fig_pie = go.Figure(go.Pie(
                labels=labels, values=values,
                hole=0.45,
                marker_colors=["#22c55e", "#eab308", "#f97316", "#ef4444"],
            ))
            fig_pie.update_layout(title="Recommendation Breakdown", height=280,
                                   margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig_pie, use_container_width=True)

        # Data table
        st.subheader("📋 Full Results Table")
        df = pd.DataFrame([{
            "Rank":       c["rank"],
            "Name":       c["name"],
            "Email":      c["email"],
            "Skill %":    c["skill_score"],
            "Semantic %": c["semantic_score"],
            "Final %":    c["final_score"],
            "Experience": f"{c['years_exp']}y" if c.get("years_exp") else "N/A",
            "Status":     c["recommendation"],
        } for c in ranked])
        st.dataframe(df, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Results CSV", csv, "screening_results.csv", "text/csv")

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 3 — Candidate Details
    # ─────────────────────────────────────────────────────────────────────────
    with tab3:
        if "ranked" not in st.session_state:
            st.info("Run the screening pipeline first (Tab 1).")
            return

        ranked = st.session_state["ranked"]
        jd_text = st.session_state.get("jd_text", "")

        from skill_matcher import extract_skills_from_text
        jd_skills = extract_skills_from_text(jd_text)

        selected_name = st.selectbox(
            "Select candidate",
            [f"#{c['rank']} — {c['name']}" for c in ranked],
        )
        idx = int(selected_name.split("—")[0].strip()[1:]) - 1
        c = ranked[idx]

        # Header row
        st.markdown(f"## {c['name']}  {c['recommendation']}")
        info_cols = st.columns(4)
        info_cols[0].markdown(f"📧 `{c['email'] or 'N/A'}`")
        info_cols[1].markdown(f"📞 `{c['phone'] or 'N/A'}`")
        info_cols[2].markdown(f"🔗 `{c['linkedin'] or 'N/A'}`")
        info_cols[3].markdown(f"💻 `{c['github'] or 'N/A'}`")

        # Gauges
        g1, g2, g3 = st.columns(3)
        with g1:
            st.plotly_chart(score_gauge(c["skill_score"],    "Skill Match"),    use_container_width=True)
        with g2:
            st.plotly_chart(score_gauge(c["semantic_score"], "Semantic Match"), use_container_width=True)
        with g3:
            st.plotly_chart(score_gauge(c["final_score"],    "Final Score"),    use_container_width=True)

        # Skills
        skill_col, radar_col = st.columns([1, 1])
        with skill_col:
            st.markdown("#### ✅ Matched Skills")
            if c["matched_skills"]:
                chips = " ".join([f'<span class="skill-chip">{s}</span>' for s in c["matched_skills"]])
                st.markdown(chips, unsafe_allow_html=True)
            else:
                st.caption("No matched skills detected.")

            st.markdown("#### ❌ Missing Skills")
            if c["missing_skills"]:
                chips = " ".join([f'<span class="missing-chip">{s}</span>' for s in c["missing_skills"]])
                st.markdown(chips, unsafe_allow_html=True)
            else:
                st.caption("No missing skills — full match!")

        with radar_col:
            if jd_skills:
                radar = skill_coverage_radar(c, jd_skills[:12])  # cap at 12 axes
                if radar:
                    st.markdown("#### 🕸️ Skill Coverage Radar")
                    st.plotly_chart(radar, use_container_width=True)

        # Education
        if c.get("education"):
            st.markdown("#### 🎓 Education")
            for edu in c["education"]:
                st.markdown(f"- {edu}")

        # Raw resume
        with st.expander("📄 View Raw Resume Text"):
            st.text(c["raw_text"])


if __name__ == "__main__":
    # Warm up model in background
    warm_up_model()
    main()
