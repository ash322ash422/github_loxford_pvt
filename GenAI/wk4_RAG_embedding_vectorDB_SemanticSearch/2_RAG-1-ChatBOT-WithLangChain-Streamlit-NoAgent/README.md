# RAG Chatbot — LangChain + Pinecone + OpenAI

A Retrieval-Augmented Generation (RAG) chatbot that lets you upload PDF documents and ask questions about them. Documents are embedded and stored in Pinecone once; all subsequent runs skip re-ingestion and connect directly to the existing index.

---

## Table of Contents

- [RAG Chatbot — LangChain + Pinecone + OpenAI](#rag-chatbot--langchain--pinecone--openai)
  - [Table of Contents](#table-of-contents)
  - [Architecture Overview](#architecture-overview)
  - [Workflow](#workflow)
    - [Ingestion (first run only)](#ingestion-first-run-only)
    - [Query (every run)](#query-every-run)
    - [Smart Re-ingestion Guard](#smart-re-ingestion-guard)
  - [Project Structure](#project-structure)
  - [Tech Stack](#tech-stack)
  - [Prerequisites](#prerequisites)
  - [Setup](#setup)
    - [1. Clone or download the project](#1-clone-or-download-the-project)
    - [2. Create and activate a virtual environment](#2-create-and-activate-a-virtual-environment)
    - [3. Install dependencies](#3-install-dependencies)
    - [4. Get your API keys](#4-get-your-api-keys)
    - [5. Create a `.env` file (for CLI usage only)](#5-create-a-env-file-for-cli-usage-only)
  - [Running the App](#running-the-app)
    - [Step-by-step usage](#step-by-step-usage)
  - [Running from the CLI](#running-from-the-cli)
  - [Configuration](#configuration)
  - [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        USER (Browser)                        │
│                     Streamlit UI (app.py)                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
              ┌─────────────▼──────────────┐
              │         rag_core.py         │
              │   (all RAG logic lives here) │
              └──┬──────────────────────┬───┘
                 │                      │
    ┌────────────▼──────────┐  ┌────────▼────────────────┐
    │     OpenAI API        │  │      Pinecone API         │
    │                       │  │                           │
    │  text-embedding-3-    │  │  Serverless Vector Index  │
    │  small  (1536 dims)   │  │  cosine similarity search │
    │                       │  │  AWS us-east-1            │
    │  gpt-4o-mini          │  │                           │
    │  (answer generation)  │  │                           │
    └───────────────────────┘  └───────────────────────────┘
```

---

## Workflow

### Ingestion (first run only)

```
PDF File(s)
    │
    ▼
PyPDFLoader          ← loads each page as a Document
    │
    ▼
RecursiveCharacterTextSplitter
    chunk_size=400, chunk_overlap=100
    │
    ▼
OpenAI Embeddings    ← text-embedding-3-small (1536 dimensions)
    │
    ▼
Pinecone Upsert      ← vectors + metadata stored in serverless index
```

### Query (every run)

```
User Question
    │
    ▼
OpenAI Embeddings    ← embed the question (same model as ingestion)
    │
    ▼
Pinecone Similarity Search
    top-k=3 most relevant chunks retrieved
    │
    ▼
Prompt Assembly      ← question + retrieved context combined
    │
    ▼
gpt-4o-mini          ← generates a grounded answer
    │
    ▼
Answer displayed in Streamlit chat UI
```

### Smart Re-ingestion Guard

On every run, before touching any PDF, the app checks Pinecone's `describe_index_stats()`:

```
App starts
    │
    ├── Index missing or empty?  ──► load PDF → split → embed → upsert
    │
    └── Index already has vectors? ──► skip everything, connect directly
```

This means you only ever pay for embeddings and upserts **once**, regardless of how many times you restart the app.

---

## Project Structure

```
your-project/
│
├── app.py              # Streamlit UI — sidebar keys, file upload, chat interface
├── rag_core.py         # All RAG logic — loading, splitting, embedding, retrieval, LLM
├── requirements.txt    # Pinned dependencies
├── .env                # API keys (never commit this file)
└── README.md           # This file
```

---

## Tech Stack

| Component | Library | Version |
|---|---|---|
| UI | Streamlit | 1.45.1 |
| RAG orchestration | LangChain | 1.3.6 |
| Document loaders | langchain-community | 0.4.2 |
| OpenAI integration | langchain-openai | 1.2.2 |
| Vector store integration | langchain-pinecone | 0.2.13 |
| Text splitting | langchain-text-splitters | 1.1.2 |
| Vector database | Pinecone | 7.3.0 |
| LLM + Embeddings | OpenAI (gpt-4o-mini, text-embedding-3-small) | — |
| PDF parsing | pypdf | 6.10.2 |
| Env variable loading | python-dotenv | 1.2.2 |

---

## Prerequisites

- Python 3.10 or higher
- An [OpenAI account](https://platform.openai.com) with a funded API key
- A [Pinecone account](https://app.pinecone.io) (free Starter plan is sufficient)

---

## Setup

### 1. Clone or download the project

```bash
git clone <your-repo-url>
cd your-project
```

### 2. Create and activate a virtual environment

```bash
# Create
python -m venv venv

# Activate — macOS / Linux
source venv/bin/activate

# Activate — Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get your API keys

**OpenAI API Key**
1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Click **Create new secret key**
3. Copy the key (starts with `sk-...`)

**Pinecone API Key**
1. Go to [app.pinecone.io](https://app.pinecone.io)
2. Sign up for a free account if you don't have one
3. Navigate to **API Keys** in the left sidebar
4. Click **Create API key**, copy the key (starts with `pcsk-...`)

> The Pinecone index (`rag-index`) is created **automatically** on first run. You do not need to create it manually.

### 5. Create a `.env` file (for CLI usage only)

If you plan to use the CLI test mode (`python rag_core.py`), create a `.env` file in the project root:

```bash
# .env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pcsk-...
```

> **Important:** Never commit `.env` to version control. Add it to `.gitignore`:
> ```bash
> echo ".env" >> .gitignore
> ```

When using the **Streamlit app**, API keys are entered directly in the sidebar — no `.env` file is needed.

---

## Running the App

```bash
streamlit run app.py
```

The app opens automatically in your browser at `http://localhost:8501`.

### Step-by-step usage

1. **Enter API keys** in the left sidebar
   - OpenAI API Key (`sk-...`)
   - Pinecone API Key (`pcsk-...`)

2. **Upload PDF(s)** using the file uploader
   - First upload: chunks the PDF, generates embeddings, and upserts to Pinecone
   - Subsequent runs: detects existing vectors and skips re-ingestion automatically

3. **Ask questions** in the chat input at the bottom
   - The app retrieves the 3 most relevant chunks from Pinecone
   - GPT-4o-mini generates a grounded answer from that context
   - Expand **"View source chunks"** under any answer to inspect what was retrieved

4. **Clear chat history** with the button that appears after the first message

---

## Running from the CLI

For testing without Streamlit, run `rag_core.py` directly:

```bash
python rag_core.py
```

This requires:
- A `.env` file with both API keys (see Setup step 5)
- A PDF file named `document-loxford-company.pdf` in the same directory (or edit the `test_pdf` variable in the `__main__` block)

The CLI enters an interactive loop:

```
==================================================
  RAG Chat ready. Type 'exit' to quit.
==================================================

Your question: What is this document about?

--- Retrieved Chunks ---
[Chunk 1] ...
[Chunk 2] ...
[Chunk 3] ...

--- Answer ---
This document is about ...

Your question: exit
Goodbye!
```

---

## Configuration

The following values can be adjusted in `rag_core.py`:

| Parameter | Location | Default | Description |
|---|---|---|---|
| `chunk_size` | `load_and_split_pdfs()` | `1000` | Max characters per chunk |
| `chunk_overlap` | `load_and_split_pdfs()` | `100` | Overlap between consecutive chunks |
| `k` | `get_retriever()` | `3` | Number of chunks retrieved per query |
| `model` (embeddings) | `_make_embeddings()` | `text-embedding-3-small` | OpenAI embedding model |
| `model` (LLM) | `ask_llm()` | `gpt-4o-mini` | OpenAI chat model |
| `cloud` / `region` | `_get_or_create_index()` | `aws` / `us-east-1` | Pinecone serverless region |
| `index_name` | Streamlit sidebar / CLI | `rag-index` | Pinecone index name |

---

## Troubleshooting

**`Error during ingestion: Pinecone API key must be provided`**
The Pinecone key was not committed to session state before ingestion fired. Make sure you press Enter (or click outside the field) after typing your Pinecone API key in the sidebar, then upload your PDF. The key must be saved before the file uploader triggers.

**`openai.AuthenticationError`**
Your OpenAI API key is invalid or has no credit. Check [platform.openai.com/usage](https://platform.openai.com/usage).

**`pinecone.exceptions.UnauthorizedException`**
Your Pinecone API key is incorrect. Re-copy it from [app.pinecone.io](https://app.pinecone.io) → API Keys.

**Index keeps re-ingesting on every run**
This happens if the index name in the sidebar does not match the index that was previously populated. Make sure the **Pinecone Index Name** field in the sidebar matches exactly what was used during the first ingest.

**Answers are vague or incorrect**
Try reducing `chunk_size` (e.g. to `500`) and increasing `k` (e.g. to `5`) in `rag_core.py` to give the LLM more targeted context. A smaller chunk size improves retrieval precision for detailed questions.

**PDF not loading**
Ensure the PDF is not password-protected and is text-based (not a scanned image). Image-based PDFs require OCR preprocessing (e.g. with `pytesseract`) which is not included in this setup.