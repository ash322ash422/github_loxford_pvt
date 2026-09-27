# rag_core.py

import os
import tempfile
import time

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore

from pinecone import Pinecone, ServerlessSpec


# -------- LOAD + SPLIT --------
def load_and_split_pdfs(files):
    all_docs = []

    for file in files:
        if hasattr(file, "read"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file.read())
                file_path = tmp.name
            owns_tmp = True
        else:
            file_path = file
            owns_tmp = False

        try:
            loader = PyPDFLoader(file_path)
            docs = loader.load()
        finally:
            if owns_tmp:
                os.unlink(file_path)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
        )
        all_docs.extend(splitter.split_documents(docs))

    return all_docs


# -------- HELPERS --------
def _make_embeddings(openai_api_key):
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=openai_api_key,
    )


def _make_pinecone_client(pinecone_api_key):
    """Always build the client explicitly — never read from env vars."""
    return Pinecone(api_key=pinecone_api_key)


def _get_or_create_index(pc, index_name):
    """Create the serverless index if absent, wait until ready, return Index object."""
    existing = [idx.name for idx in pc.list_indexes()]
    if index_name not in existing:
        print(f"  Creating Pinecone index '{index_name}' ...")
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        while not pc.describe_index(index_name).status["ready"]:
            print("  Waiting for index to be ready...")
            time.sleep(2)
        print("  Index ready.")
    return pc.Index(index_name)


def index_is_populated(pc, index_name):
    """Returns True if the index exists AND has at least one vector."""
    existing = [idx.name for idx in pc.list_indexes()]
    if index_name not in existing:
        return False
    stats = pc.Index(index_name).describe_index_stats()
    return stats.get("total_vector_count", 0) > 0


def _vectorstore_from_index(pinecone_index, embeddings):
    """
    Single place that constructs PineconeVectorStore.
    Always uses the pre-built Index object — never passes index_name or
    pinecone_api_key as kwargs, which are broken in langchain-pinecone >= 0.2.
    """
    return PineconeVectorStore(index=pinecone_index, embedding=embeddings)


# -------- BUILD / CONNECT VECTOR STORE --------
def build_vector_store(docs, openai_api_key, pinecone_api_key, index_name="rag-index"):
    """
    - Index missing          → create, upsert docs
    - Index empty            → upsert docs
    - Index already has data → skip upsert, just connect
    """
    embeddings    = _make_embeddings(openai_api_key)
    pc            = _make_pinecone_client(pinecone_api_key)
    pinecone_index = _get_or_create_index(pc, index_name)

    if index_is_populated(pc, index_name):
        print(f"  Index '{index_name}' already populated — skipping upsert.")
        return _vectorstore_from_index(pinecone_index, embeddings)

    # First-time upsert — add_texts gives us full control over the client
    print(f"  Upserting {len(docs)} chunks into '{index_name}' ...")
    vectorstore = _vectorstore_from_index(pinecone_index, embeddings)
    texts    = [doc.page_content for doc in docs]
    metadatas = [doc.metadata   for doc in docs]
    vectorstore.add_texts(texts, metadatas=metadatas)
    print("  Upsert complete.")
    return vectorstore


def load_vector_store(openai_api_key, pinecone_api_key, index_name="rag-index"):
    """Connect to an existing index without re-uploading."""
    embeddings    = _make_embeddings(openai_api_key)
    pc            = _make_pinecone_client(pinecone_api_key)
    pinecone_index = pc.Index(index_name)
    return _vectorstore_from_index(pinecone_index, embeddings)


# -------- RETRIEVER --------
def get_retriever(vectorstore, k=3):
    return vectorstore.as_retriever(search_kwargs={"k": k})


# -------- ASK LLM --------
def ask_llm(question, retriever, openai_api_key):
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=openai_api_key,
    )

    docs    = retriever.invoke(question)
    context = "\n\n".join([doc.page_content for doc in docs])

    prompt = f"""Answer using the context below. Keep it short.

            Context:
            {context}

            Question: {question}
    """

    response = llm.invoke(prompt)
    return response.content, docs

