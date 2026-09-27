from openai import OpenAI
import numpy as np
import faiss
from pypdf import PdfReader

# from dotenv import load_dotenv
import os

# load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY)


# -------- READ PDF --------
def read_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


# -------- CHUNK TEXT --------
def chunk_text(text, size=300):
    return [text[i:i+size] for i in range(0, len(text), size)]


# -------- EMBEDDINGS --------
def embed(texts):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return np.array([d.embedding for d in response.data]).astype("float32")


# -------- BUILD VECTOR DB --------
def build_index(chunks):
    embeddings = embed(chunks)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    return index, chunks


# -------- RETRIEVE --------
def retrieve(query, index, chunks, k=3):
    q_emb = embed([query])
    distances, indices = index.search(q_emb, k)
    return [chunks[i] for i in indices[0]]


# -------- ASK LLM --------
def ask_llm(question, context):
    prompt = f"""
    Answer using the context below. Keep it short.

    Context:
    {context}

    Question: {question}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content
