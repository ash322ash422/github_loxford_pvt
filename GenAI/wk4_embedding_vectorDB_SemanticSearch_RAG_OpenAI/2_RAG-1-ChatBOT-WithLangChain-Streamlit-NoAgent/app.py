# app.py  —  Streamlit RAG Chatbot (Pinecone edition)
#
# Run with:  streamlit run app.py
# Expects rag_core.py in the same directory.

import streamlit as st
from pinecone import Pinecone
from rag_core import (
    load_and_split_pdfs,
    build_vector_store,
    load_vector_store,
    get_retriever,
    ask_llm,
    index_is_populated,
)

# ------------------------------------------------------------------ #
#  PAGE CONFIG                                                         #
# ------------------------------------------------------------------ #
st.set_page_config(page_title="RAG Chatbot", page_icon="🤖", layout="wide")
st.title("🤖 RAG Chatbot — LangChain + Pinecone")

# ------------------------------------------------------------------ #
#  SESSION STATE — initialise all keys up front                       #
# ------------------------------------------------------------------ #
for key, default in {
    "retriever": None,
    "chat_history": [],
    "openai_key": "",
    "pinecone_key": "",
    "index_name": "rag-index",
    "ingestion_done": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ------------------------------------------------------------------ #
#  SIDEBAR — API keys + index settings                                #
# ------------------------------------------------------------------ #
with st.sidebar:
    st.header("🔑 API Keys")

    # Use on_change to immediately commit values into session_state
    def save_openai_key():
        st.session_state.openai_key = st.session_state._openai_input

    def save_pinecone_key():
        st.session_state.pinecone_key = st.session_state._pinecone_input

    def save_index_name():
        st.session_state.index_name = st.session_state._index_input
        # Reset retriever so re-connection fires on next run
        st.session_state.retriever = None
        st.session_state.ingestion_done = False

    st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-...",
        key="_openai_input",
        on_change=save_openai_key,
        help="Used for embeddings (text-embedding-3-small) and GPT-4o-mini.",
    )

    st.text_input(
        "Pinecone API Key",
        type="password",
        placeholder="pcsk-...",
        key="_pinecone_input",
        on_change=save_pinecone_key,
        help="From app.pinecone.io → API Keys.",
    )

    st.divider()

    st.header("⚙️ Index Settings")
    st.text_input(
        "Pinecone Index Name",
        value=st.session_state.index_name,
        key="_index_input",
        on_change=save_index_name,
        help="Will be created automatically if it doesn't exist.",
    )

    st.divider()

    # Live vector-count badge (only when both keys are present)
    pc_key  = st.session_state.pinecone_key
    idx_name = st.session_state.index_name
    if pc_key and idx_name:
        try:
            _pc = Pinecone(api_key=pc_key)
            if index_is_populated(_pc, idx_name):
                _stats = _pc.Index(idx_name).describe_index_stats()
                _count = _stats.get("total_vector_count", 0)
                st.success(f"✅ Index connected\n\n**{_count:,}** vectors stored")
            else:
                st.info("ℹ️ Index is empty — upload a PDF to populate it.")
        except Exception as _e:
            st.warning(f"Could not reach Pinecone:\n{_e}")

    st.divider()
    st.caption("Built with LangChain · Pinecone · OpenAI")

# ------------------------------------------------------------------ #
#  GATE: require both keys before doing anything                      #
# ------------------------------------------------------------------ #
openai_api_key   = st.session_state.openai_key
pinecone_api_key = st.session_state.pinecone_key
index_name       = st.session_state.index_name

if not openai_api_key or not pinecone_api_key:
    st.info("👈 Enter your **OpenAI** and **Pinecone** API keys in the sidebar to get started.")
    st.stop()

# ------------------------------------------------------------------ #
#  FILE UPLOAD + INGESTION                                            #
# ------------------------------------------------------------------ #
st.subheader("📄 Upload Documents")

uploaded_files = st.file_uploader(
    "Upload one or more PDF files",
    type="pdf",
    accept_multiple_files=True,
    help="Documents are chunked, embedded, and stored in Pinecone once. "
         "Re-uploading won't duplicate — upsert is skipped if the index is already populated.",
)

# ---- Connect or ingest ----
if uploaded_files and st.session_state.retriever is None:
    with st.spinner("Processing PDFs and connecting to Pinecone..."):
        try:
            docs = load_and_split_pdfs(uploaded_files)
            vectorstore = build_vector_store(
                docs,
                openai_api_key=openai_api_key,
                pinecone_api_key=pinecone_api_key,
                index_name=index_name,
            )
            st.session_state.retriever = get_retriever(vectorstore)
            st.session_state.ingestion_done = True
            st.success(f"✅ Ready! {len(docs)} chunks processed.")
        except Exception as e:
            st.error(f"Error during ingestion: {e}")
            st.stop()

elif not uploaded_files and st.session_state.retriever is None:
    # No file uploaded — try connecting to an existing populated index
    try:
        _pc = Pinecone(api_key=pinecone_api_key)
        if index_is_populated(_pc, index_name):
            with st.spinner("Connecting to existing Pinecone index..."):
                vectorstore = load_vector_store(openai_api_key, pinecone_api_key, index_name)
                st.session_state.retriever = get_retriever(vectorstore)
            st.success("✅ Connected to existing index. Ready to chat!")
        else:
            st.info("Upload PDF(s) above to populate the index and start chatting.")
    except Exception as e:
        st.warning(f"Could not connect to existing index: {e}")

# ------------------------------------------------------------------ #
#  CHAT UI                                                            #
# ------------------------------------------------------------------ #
st.divider()
st.subheader("💬 Chat")

# Render existing conversation
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# New question input
question = st.chat_input(
    "Ask a question about your documents...",
    disabled=(st.session_state.retriever is None),
)

if question:
    if st.session_state.retriever is None:
        st.warning("⚠️ Upload a PDF first so the index has content to search.")
        st.stop()

    # Show user message
    st.session_state.chat_history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # Generate & display answer
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer, source_docs = ask_llm(
                    question,
                    st.session_state.retriever,
                    openai_api_key,          # always fresh from session_state
                )
            except Exception as e:
                answer = f"❌ Error: {e}"
                source_docs = []

        st.markdown(answer)

        # Expandable source chunks
        if source_docs:
            with st.expander("📚 View source chunks", expanded=False):
                for i, doc in enumerate(source_docs):
                    page   = doc.metadata.get("page", "N/A")
                    source = doc.metadata.get("source", "")
                    st.markdown(
                        f"**Chunk {i+1}** — page {page}"
                        + (f" · `{source}`" if source else "")
                    )
                    st.text(doc.page_content)
                    st.divider()

    st.session_state.chat_history.append({"role": "assistant", "content": answer})

# ---- Clear chat button ----
if st.session_state.chat_history:
    if st.button("🗑️ Clear chat history"):
        st.session_state.chat_history = []
        st.rerun()