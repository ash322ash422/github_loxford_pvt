"""
app.py — Streamlit UI for the Fraud Detection Multi-Agent System.
Run with:  streamlit run app.py
"""

import os, json, time, random
import streamlit as st
from datetime import datetime

from agents.workflow import run_workflow

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Fraud Detection · Multi-Agent",
    page_icon="🛡️",
    layout="wide",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.badge {
    display:inline-block; padding:4px 14px; border-radius:20px;
    font-size:13px; font-weight:600; letter-spacing:.3px;
}
.badge-approve { background:#0d3321; color:#2ecc71; border:1px solid #2ecc71; }
.badge-flag    { background:#3a2a00; color:#f39c12; border:1px solid #f39c12; }
.badge-block   { background:#3a0d0d; color:#e74c3c; border:1px solid #e74c3c; }
.badge-agent   { background:#1a2a40; color:#4f8ef7; border:1px solid #4f8ef7; font-size:11px; }

.risk-bar-wrap { background:#1a1f2e; border-radius:8px; height:18px; margin:6px 0; overflow:hidden; }
.risk-bar      { height:100%; border-radius:8px; transition:width .6s ease; }

.agent-card {
    background:#1a1f2e; border:1px solid #2a2f3e;
    border-radius:10px; padding:14px 16px; margin-bottom:8px;
}
.agent-card h4 { margin:0 0 6px 0; font-size:13px; color:#8899bb; font-weight:500; }
.agent-card p  { margin:4px 0; font-size:13px; color:#dde2ef; }

.timing-chip {
    display:inline-block; background:#0e1117; border:1px solid #2a2f3e;
    border-radius:6px; padding:2px 10px; font-size:11px; color:#8899bb;
    margin-right:6px; margin-top:4px;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def risk_bar(score: float):
    pct   = int(score * 100)
    color = "#2ecc71" if score < 0.35 else "#f39c12" if score < 0.65 else "#e74c3c"
    st.markdown(
        f'<div class="risk-bar-wrap">'
        f'<div class="risk-bar" style="width:{pct}%;background:{color}"></div>'
        f'</div>'
        f'<div style="font-size:11px;color:#8899bb;text-align:right">{pct}% risk</div>',
        unsafe_allow_html=True,
    )


def decision_badge(d: str):
    cls = {"APPROVE": "badge-approve", "FLAG": "badge-flag", "BLOCK": "badge-block"}.get(d, "badge-flag")
    icon = {"APPROVE": "✅", "FLAG": "⚠️", "BLOCK": "🚫"}.get(d, "⚠️")
    st.markdown(f'<span class="badge {cls}">{icon} {d}</span>', unsafe_allow_html=True)


SAMPLE_TRANSACTIONS = [
    {
        "label": "✅ Normal purchase — low risk",
        "txn": {
            "txn_id": "TXN_DEMO_001", "customer_id": "CUST_0001",
            "amount": 49.99, "currency": "USD", "merchant": "Amazon",
            "merchant_country": "US", "channel": "web",
            "customer_email": "user1@email.com", "customer_ip": "8.8.8.8",
            "card_number": "4000000000000000",
        },
    },
    {
        "label": "⚠️ Large cross-border — medium risk",
        "txn": {
            "txn_id": "TXN_DEMO_002", "customer_id": "CUST_0050",
            "amount": 4800.00, "currency": "EUR", "merchant": "Unknown_Vendor",
            "merchant_country": "RU", "channel": "api",
            "customer_email": "user50@email.com", "customer_ip": "10.0.0.1",
            "card_number": "4000000000000001",
        },
    },
    {
        "label": "🚫 Blacklisted merchant — immediate block",
        "txn": {
            "txn_id": "TXN_DEMO_003", "customer_id": "CUST_0120",
            "amount": 299.00, "currency": "USD", "merchant": "ShadyShop",
            "merchant_country": "NG", "channel": "web",
            "customer_email": "user120@email.com", "customer_ip": "8.8.4.4",
            "card_number": "4000000000000002",
        },
    },
    {
        "label": "🚫 Stolen card + blacklisted email",
        "txn": {
            "txn_id": "TXN_DEMO_004", "customer_id": "CUST_0200",
            "amount": 9999.00, "currency": "USD", "merchant": "FastCash",
            "merchant_country": "NG", "channel": "api",
            "customer_email": "fraud123@scam.com", "customer_ip": "192.168.99.1",
            "card_number": "4111111111111111",
        },
    },
]


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛡️ Fraud Detection")
    st.markdown("**Multi-Agent System**")
    st.divider()

    openai_key = st.text_input("🔑 OpenAI API Key", type="password", placeholder="sk-...")
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key

    st.divider()
    st.markdown("#### 🤖 Agent Architecture")
    st.markdown("""
<div style='font-size:12px;color:#8899bb;line-height:1.9'>
<b style='color:#4f8ef7'>Orchestrator</b><br>
&nbsp;↓ fans out in parallel<br>
<b style='color:#c084f5'>History Agent</b><br>
&nbsp;&nbsp;↳ SQL Toolkit<br>
<b style='color:#c084f5'>Fraud Scorer Agent</b><br>
&nbsp;&nbsp;↳ Fraud Toolkit<br>
<b style='color:#c084f5'>Blacklist Agent</b><br>
&nbsp;&nbsp;↳ Blacklist Toolkit<br>
&nbsp;↓ join — all must finish<br>
<b style='color:#2ecc71'>Decision Agent</b><br>
&nbsp;&nbsp;↳ Final verdict
</div>
""", unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 🧪 Sample Transactions")
    for s in SAMPLE_TRANSACTIONS:
        if st.button(s["label"], use_container_width=True, key=s["txn"]["txn_id"]):
            st.session_state["loaded_txn"] = s["txn"]


# ── Main ───────────────────────────────────────────────────────────────────────
st.markdown("# 🛡️ Real-Time Fraud Detection")
st.markdown("Three specialist agents run **in parallel** then a Decision Agent merges their signals.")

tab_input, tab_results, tab_deep = st.tabs([
    "📝  Transaction Input",
    "📊  Decision & Results",
    "🔬  Deep Dive",
])


# ── TAB 1: Input ───────────────────────────────────────────────────────────────
with tab_input:
    loaded = st.session_state.get("loaded_txn", {})

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Customer & Transaction")
        customer_id = st.text_input("Customer ID", value=loaded.get("customer_id", "CUST_0001"))
        amount      = st.number_input("Amount", value=float(loaded.get("amount", 150.0)), min_value=0.01)
        currency    = st.selectbox("Currency", ["USD","GBP","EUR","INR","SGD"],
                                    index=["USD","GBP","EUR","INR","SGD"].index(loaded.get("currency","USD")))
        merchant    = st.text_input("Merchant", value=loaded.get("merchant", "Amazon"))

    with col2:
        st.markdown("#### Channel & Identity")
        merchant_country = st.selectbox("Merchant Country",
            ["US","GB","IN","SG","DE","FR","AU","CA","NG","RU"],
            index=["US","GB","IN","SG","DE","FR","AU","CA","NG","RU"].index(
                loaded.get("merchant_country","US")))
        channel      = st.selectbox("Channel", ["web","mobile","pos","api"],
                                    index=["web","mobile","pos","api"].index(loaded.get("channel","web")))
        customer_email = st.text_input("Customer Email", value=loaded.get("customer_email","user@email.com"))
        customer_ip    = st.text_input("Customer IP",    value=loaded.get("customer_ip","8.8.8.8"))
        card_number    = st.text_input("Card Number",    value=loaded.get("card_number","4000000000000000"))

    run_btn = st.button("🚀  Run Fraud Analysis", type="primary", use_container_width=True)

    if run_btn:
        if not os.environ.get("OPENAI_API_KEY"):
            st.error("⚠️  Enter your OpenAI API Key in the sidebar.")
            st.stop()

        txn = {
            "txn_id":           f"TXN_{random.randint(10000,99999)}",
            "customer_id":      customer_id,
            "amount":           amount,
            "currency":         currency,
            "merchant":         merchant,
            "merchant_country": merchant_country,
            "channel":          channel,
            "customer_email":   customer_email,
            "customer_ip":      customer_ip,
            "card_number":      card_number,
        }

        with st.spinner("⚡ Running 3 agents in parallel…"):
            result = run_workflow(txn)

        st.session_state["result"] = result
        st.success("✅  Analysis complete — see Results tab")


# ── TAB 2: Results ─────────────────────────────────────────────────────────────
with tab_results:
    result = st.session_state.get("result")
    if not result:
        st.info("Run a transaction analysis from the Input tab.")
    else:
        decision = result.get("decision", "FLAG")
        score    = result.get("risk_score", 0.5)
        timing   = result.get("timing", {})

        # ── Decision banner ────────────────────────────────────────────
        st.markdown("### Final Decision")
        decision_badge(decision)
        st.markdown("")
        risk_bar(score)

        # ── Timing chips ───────────────────────────────────────────────
        st.markdown("**Agent timing (parallel execution):**")
        chips = ""
        for k, v in timing.items():
            label = k.replace("_ms","").replace("_"," ")
            chips += f'<span class="timing-chip">⏱ {label}: {v} ms</span>'
        st.markdown(chips, unsafe_allow_html=True)
        st.markdown("")

        # ── Explanation ────────────────────────────────────────────────
        st.markdown("### Compliance Explanation")
        st.info(result.get("explanation",""))

        # ── Reasons ───────────────────────────────────────────────────
        reasons = result.get("reasons", [])
        if reasons:
            st.markdown("### Key Reasons")
            for r in reasons:
                icon = "🔴" if decision == "BLOCK" else "🟡" if decision == "FLAG" else "🟢"
                st.markdown(f"{icon} {r}")

        # ── Three agent summaries ──────────────────────────────────────
        st.markdown("### Agent Summaries")
        c1, c2, c3 = st.columns(3)

        with c1:
            h = result.get("history_result") or {}
            rl = h.get("risk_level","—")
            color = {"low":"#2ecc71","medium":"#f39c12","high":"#e74c3c","critical":"#e74c3c"}.get(rl,"#8899bb")
            st.markdown(f"""
<div class="agent-card">
  <h4>🕐 History Agent</h4>
  <p>Risk: <b style='color:{color}'>{rl.upper()}</b></p>
  <p>Score: {h.get('risk_score',0):.2f}</p>
  <p style='font-size:12px;color:#8899bb'>{h.get('summary','')}</p>
</div>""", unsafe_allow_html=True)

        with c2:
            f = result.get("fraud_result") or {}
            rl = f.get("risk_level","—")
            color = {"low":"#2ecc71","medium":"#f39c12","high":"#e74c3c","critical":"#e74c3c"}.get(rl,"#8899bb")
            st.markdown(f"""
<div class="agent-card">
  <h4>🔍 Fraud Scorer Agent</h4>
  <p>Risk: <b style='color:{color}'>{rl.upper()}</b></p>
  <p>Score: {f.get('risk_score',0):.2f}</p>
  <p style='font-size:12px;color:#8899bb'>{f.get('summary','')}</p>
</div>""", unsafe_allow_html=True)

        with c3:
            b = result.get("blacklist_result") or {}
            rl = b.get("risk_level","—")
            color = "#e74c3c" if b.get("any_hit") else "#2ecc71"
            st.markdown(f"""
<div class="agent-card">
  <h4>🚫 Blacklist Agent</h4>
  <p>Risk: <b style='color:{color}'>{rl.upper()}</b></p>
  <p>Hits: {len(b.get('hits',[]))}</p>
  <p style='font-size:12px;color:#8899bb'>{b.get('summary','')}</p>
</div>""", unsafe_allow_html=True)


# ── TAB 3: Deep Dive ───────────────────────────────────────────────────────────
with tab_deep:
    result = st.session_state.get("result")
    if not result:
        st.info("Run a transaction analysis from the Input tab.")
    else:
        st.markdown("### Raw Agent Outputs")

        with st.expander("🕐 History Agent — full output"):
            st.json(result.get("history_result", {}))

        with st.expander("🔍 Fraud Scorer Agent — signals & score"):
            st.json(result.get("fraud_result", {}))

        with st.expander("🚫 Blacklist Agent — all checks"):
            st.json(result.get("blacklist_result", {}))

        with st.expander("⚖️ Decision Agent — full state"):
            st.json({
                "decision":    result.get("decision"),
                "risk_score":  result.get("risk_score"),
                "reasons":     result.get("reasons"),
                "explanation": result.get("explanation"),
                "timing":      result.get("timing"),
            })

        st.markdown("### Transaction Submitted")
        st.json(result.get("transaction", {}))
