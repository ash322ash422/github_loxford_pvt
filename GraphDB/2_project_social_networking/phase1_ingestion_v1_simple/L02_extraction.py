from typing import List


from langchain_core.prompts import ChatPromptTemplate

from langchain_openai import ChatOpenAI
import json
from pathlib import Path
from typing import List

from pprint import pprint
from L01_chunking import semantic_chunking
from  schemas import GraphDocument
import os
from dotenv import load_dotenv

# Load variables from .env into system environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "gpt-5"

EXTRACTED_JSON = "L02_extracted_graph_documents.json"   

EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
[("system","""
    You are an expert Knowledge Graph extraction engine.

    Extract every entity and every relationship.

    Rules

    1. Return only entities that appear explicitly.
    2. Do not hallucinate.
    3. Every entity must have

    - id
    - name
    - label

    4. Entity IDs MUST follow this format

    person_alice
    person_bob
    organization_techhub
    group_dataclub
    platform_github
    product_chatapp

    Never use dots.
    Never use spaces.
    Use lowercase.
    Use underscore.


    5. Labels must be one of

    Person
    Organization
    Product
    Platform
    Group

    6. Every relationship must have

    source
    target
    relation

    7. Relation names MUST be uppercase.

    Examples

    MANAGES
    WORKS_AT
    WORKS_ON
    MEMBER_OF
    MARRIED_TO
    USES_PLATFORM
    FOLLOWS
    DEVELOPED

    Return every relationship you can infer directly from the text.
"""
),
("human","{text}")]
)


llm = ChatOpenAI( api_key=OPENAI_API_KEY, model=MODEL_NAME, temperature=0)

structured_llm = llm.with_structured_output(GraphDocument)

def extract_graph(chunk: dict) -> GraphDocument:
    """    Extract graph from one chunk.    """

    chain = EXTRACTION_PROMPT | structured_llm
    graph = chain.invoke({"text": chunk["text"]})
    graph.chunk_id = chunk["chunk_id"]
    
    return graph



def save_graph_documents(
    graph_documents: List[GraphDocument],
    filename: str = EXTRACTED_JSON
) -> None:
    """
    Save GraphDocument objects as JSON.

    Parameters
    ----------
    graph_documents : List[GraphDocument]
    filename : str
    """

    Path(filename).parent.mkdir(parents=True, exist_ok=True)

    data = [
        graph.model_dump(mode="json")
        for graph in graph_documents
    ]

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )

    print(f"\nSaved {len(graph_documents)} GraphDocuments -> {filename}")
    
def load_graph_documents(filename: str=EXTRACTED_JSON) -> List[GraphDocument]:
    """
    Load GraphDocument objects from JSON.
    """

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph_documents = [
        GraphDocument.model_validate(item)
        for item in data
    ]

    print(f"Loaded {len(graph_documents)} GraphDocuments from {filename}")

    return graph_documents


if __name__ == "__main__":
    # Read Input Document
    DATA_FILE = "data.txt"
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    # Step 1 : Semantic Chunking
    print("=" * 80)
    print("STEP 1 : SEMANTIC CHUNKING")
    print("=" * 80)

    chunks = semantic_chunking(
        text=text,
        chunk_size=600,
        chunk_overlap=20
    )

    print(f"\nTotal Chunks : {len(chunks)}\n")

    for chunk in chunks:
        print("-" * 80)
        print(f"Chunk ID   : {chunk['chunk_id']}")
        print(f"Paragraph  : {chunk['metadata']['paragraph']}")
        print(f"Length     : {chunk['metadata']['length']}")
        print()
        print(chunk["text"])
        print()

    # Step 2 : LLM Extraction
    print("\n")
    print("=" * 80)
    print("STEP 2 : KNOWLEDGE GRAPH EXTRACTION")
    print("=" * 80)

    graph_documents = []

    for chunk in chunks:
        print(f"\nProcessing Chunk {chunk['chunk_id']}...")
        graph = extract_graph(chunk)
        graph_documents.append(graph)
        print("\nEntities")
        print("-" * 40)

        for entity in graph.entities:
            pprint(entity.model_dump())

        print("\nRelationships")
        print("-" * 40)

        for relationship in graph.relationships:
            pprint(relationship.model_dump())

    # save the graph documents to a JSON file
    save_graph_documents(graph_documents, EXTRACTED_JSON)
    
    # Load the graph documents from the JSON file
    graph_documents = load_graph_documents(EXTRACTED_JSON)
    
    # Summary
    print("\n")
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_entities = sum(len(g.entities) for g in graph_documents)
    total_relationships = sum(len(g.relationships) for g in graph_documents)

    print(f"Chunks Processed      : {len(chunks)}")
    print(f"Graph Documents       : {len(graph_documents)}")
    print(f"Entities Extracted    : {total_entities}")
    print(f"Relationships Created : {total_relationships}")
