import streamlit as st
from R06_graph_rag_service import GraphRAGService


# ============================================================
# Page Configuration
# ============================================================

st.set_page_config(
    page_title="GraphRAG Demo",
    page_icon="🕸️",
    layout="wide"
)

st.title("🕸️ GraphRAG Demo")
st.markdown("### Ask questions over your Knowledge Graph")


# ============================================================
# Load GraphRAG Service
# ============================================================

@st.cache_resource
def load_service():
    return GraphRAGService()


service = load_service()


# ============================================================
# Session State
# ============================================================

if "question" not in st.session_state:
    st.session_state.question = ""

if "result" not in st.session_state:
    st.session_state.result = None

if "history" not in st.session_state:
    st.session_state.history = []


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:

    st.header("📌 Sample Questions")

    samples = [
        "Who manages Bob ?",
        "Which organizations is Bob associated with ?",
        "How is Alice connected to Diana ?",
    ]

    for q in samples:

        if st.button(q, use_container_width=True):
            st.session_state.question = q

    st.divider()

    if st.button("🗑 Clear History", use_container_width=True):

        st.session_state.history = []
        st.session_state.result = None

    st.divider()

    st.markdown("### Conversation History")

    if len(st.session_state.history) == 0:

        st.info("No questions asked yet.")

    else:

        for i, item in enumerate(reversed(st.session_state.history), start=1):

            if st.button(
                item["question"],
                key=f"history_{i}",
                use_container_width=True,
            ):
                st.session_state.question = item["question"]
                st.session_state.result = item["result"]


# ============================================================
# Question Input
# ============================================================

question = st.text_input(
    "Question",
    value=st.session_state.question,
    placeholder="Ask a GraphRAG question...",
)

col1, col2 = st.columns([1, 5])

with col1:

    ask = st.button(
        "🚀 Ask",
        use_container_width=True,
    )

with col2:

    st.empty()


# ============================================================
# Query GraphRAG
# ============================================================

if ask and question.strip():

    with st.spinner("Generating Cypher and querying graph..."):

        result = service.ask(question)

    st.session_state.result = result

    st.session_state.history.append(
        {
            "question": question,
            "result": result,
        }
    )

    st.session_state.question = question


# ============================================================
# Display Results
# ============================================================

if st.session_state.result is not None:

    result = st.session_state.result

    st.divider()

    st.subheader("💬 Answer")

    st.success(result["answer"])

    confidence = float(result.get("confidence", 0))

    st.metric(
        "Confidence",
        f"{confidence:.2f}",
    )

    st.progress(confidence)

    st.divider()

    col_left, col_right = st.columns(2)

    # --------------------------------------------------------
    # Cypher
    # --------------------------------------------------------

    with col_left:

        st.subheader("🧩 Generated Cypher")

        st.code(
            result["cypher"],
            language="sql",
        )

    # --------------------------------------------------------
    # Graph Data
    # --------------------------------------------------------

    with col_right:

        st.subheader("📊 Retrieved Graph")

        with st.expander(
            "View Graph Data",
            expanded=True,
        ):
            st.json(result["graph_data"])


# ============================================================
# Footer
# ============================================================

st.divider()

st.caption(
    "GraphRAG Demo • Neo4j • OpenAI"
)