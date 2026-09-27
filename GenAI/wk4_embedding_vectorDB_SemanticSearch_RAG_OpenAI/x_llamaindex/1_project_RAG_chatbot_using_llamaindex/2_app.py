import os
import tempfile
import streamlit as st

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Settings
)

from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.chat_engine import ContextChatEngine

from llama_index.llms.openai import OpenAI

from util import save_chat_to_csv
import uuid # for session  id generation

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="Document Chatbot",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Chat With Your Documents")

# OPENAI KEY

OPENAI_API_KEY = st.sidebar.text_input(
    "OpenAI API Key",
    type="password"
)

if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY


# SESSION VARIABLES

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "chat_engine" not in st.session_state:
    st.session_state.chat_engine = None

if "index" not in st.session_state:
    st.session_state.index = None

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


# FILE UPLOAD

uploaded_files = st.file_uploader(
    "Upload PDF, TXT",
    type=["pdf", "txt"],
    accept_multiple_files=True
)

build_index = st.button("Build Knowledge Base")

# BUILD INDEX
if build_index and uploaded_files:
    with st.spinner("Reading documents..."):
        temp_dir = tempfile.mkdtemp()

        for uploaded_file in uploaded_files:
            file_path = os.path.join(
                temp_dir,
                uploaded_file.name
            )

            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

        documents = SimpleDirectoryReader(temp_dir).load_data()

        st.success(f"Loaded {len(documents)} document(s)")

        # LLM
        Settings.llm = OpenAI(
            model="gpt-4o-mini",
            temperature=0
        )

        # Create index
        index = VectorStoreIndex.from_documents(documents)

        # Memory
        memory = ChatMemoryBuffer.from_defaults(token_limit=4000)

        # Retriever
        retriever = index.as_retriever(similarity_top_k=3)

        # Chat Engine
        chat_engine = ContextChatEngine.from_defaults(
            retriever=retriever,
            memory=memory,
            system_prompt="""
                You are a finance assistant.

                Do not use LaTeX notation.
                Do not use \\frac, \\text, or mathematical markup.

                Write calculations in plain text.

                Example:

                ROA = Net Profit / Total Assets
                ROA = 20 / 110 = 18.18%
            """
        )

        st.session_state.index = index
        st.session_state.chat_engine = chat_engine

        st.success("✅ Knowledge Base Ready")


# ---------------------------------------------------
# DISPLAY CHAT HISTORY
# ---------------------------------------------------

for message in st.session_state.chat_history:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ---------------------------------------------------
# CHAT
# ---------------------------------------------------

if st.session_state.chat_engine:

    prompt = st.chat_input(
        "Ask a question about your documents..."
    )

    if prompt:

        st.session_state.chat_history.append(
            {
                "role": "user",
                "content": prompt
            }
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):

            with st.spinner("Thinking..."):

                response = st.session_state.chat_engine.chat(prompt)
                answer = str(response)
                st.markdown(answer)
                
                # OPTIONAL                
                save_chat_to_csv(question=prompt, answer=answer, session_id=st.session_state.session_id) 
                

        st.session_state.chat_history.append(
            {
                "role": "assistant",
                "content": answer
            }
        )

else:
    st.info("Upload documents and click 'Build Knowledge Base'.")