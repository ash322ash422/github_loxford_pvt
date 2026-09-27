import streamlit as st
from rag_core import read_pdf, chunk_text, build_index, retrieve, ask_llm

import os
api_key = os.getenv("OPENAI_API_KEY")

st.title("Simple PDF RAG Chatbot")

# -------- UPLOAD --------
uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

if uploaded_file:
    if "index" not in st.session_state:
        with st.spinner("Processing PDF..."):
            text = read_pdf(uploaded_file)
            chunks = chunk_text(text)
            # print("Number of chunks:", len(chunks)) # 10 chunks. You can print chunks
            index, chunks = build_index(chunks)

            st.session_state.index = index
            st.session_state.chunks = chunks

        st.success("PDF processed and stored in vector DB!")

# -------- CHAT --------
question = st.chat_input("Ask a question")

if question:
    if "index" not in st.session_state:
        st.warning("Upload a PDF first!")
        st.stop()

    index = st.session_state.index
    chunks = st.session_state.chunks

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            retrieved = retrieve(question, index, chunks)
            context = "\n".join(retrieved)
            
            st.write("### Retrieved Context from VectorDB.")
            st.write(context)
            
            answer = ask_llm(question, context)
            st.write("### Response from LLM:")
            st.write(answer)
