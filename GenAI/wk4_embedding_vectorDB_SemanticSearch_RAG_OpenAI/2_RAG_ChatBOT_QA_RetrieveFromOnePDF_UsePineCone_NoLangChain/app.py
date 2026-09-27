import streamlit as st
from step_2_rag_core import read_pdf, chunk_text, build_index, retrieve, ask_llm

st.title("Simple PDF RAG Chatbot (Pinecone Edition)")

# -------- UPLOAD --------
uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

if uploaded_file:
    # We only need to check if the index exists in the session state
    if "index" not in st.session_state:
        with st.spinner("Processing PDF and uploading to Pinecone..."):
            text = read_pdf(uploaded_file)
            chunks = chunk_text(text)
            
            # FIXED: Pinecone build_index only returns the index object
            index = build_index(chunks)

            # Store only the index client reference in session state
            st.session_state.index = index

        st.success("PDF processed and stored securely in Pinecone Vector DB!")

# -------- CHAT --------
question = st.chat_input("Ask a question")

if question:
    if "index" not in st.session_state:
        st.warning("Please upload a PDF first!")
        st.stop()

    # Grab our pinecone index reference
    index = st.session_state.index

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # FIXED: Removed the 'chunks' argument since Pinecone reads metadata from the cloud
            retrieved = retrieve(question, index, k=3)
            context = "\n".join(retrieved)
            
            st.write("### Retrieved Context from VectorDB.")
            st.write(context)
            
            answer = ask_llm(question, context)
            st.write("### Response from LLM:")
            st.write(answer)
