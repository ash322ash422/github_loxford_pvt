"""
Step 3 : Validation & Normalization
"""

import json

from L02_extraction import GraphDocument
from L03__validation_normalization import GraphValidator


INPUT_FILE = "L02_extracted_graph_documents.json"
OUTPUT_FILE = "L03_validated_graph.json"


# ----------------------------------------------------------
# Load Step-2 Output
# ----------------------------------------------------------
def load_graph_documents(filename: str):
    """
    Load GraphDocument objects from JSON.
    """

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph_documents = [
        GraphDocument.model_validate(item)
        for item in data
    ]

    print(f"Loaded {len(graph_documents)} graph documents.")

    return graph_documents


# ----------------------------------------------------------
# Save Step-3 Output
# ----------------------------------------------------------
def save_graph_documents(graph_documents, filename: str):
    """
    Save validated graph documents.
    """

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

    print(f"Saved validated graph -> {filename}")


# ----------------------------------------------------------
# Main
# ----------------------------------------------------------
def main():

    print("=" * 80)
    print("STEP 3 : VALIDATION & NORMALIZATION")
    print("=" * 80)

    # ------------------------------------------------------
    # Load extracted graph
    # ------------------------------------------------------
    graph_documents = load_graph_documents(INPUT_FILE)

    # ------------------------------------------------------
    # Validate
    # ------------------------------------------------------
    validator = GraphValidator(graph_documents)

    validated_graph = (
        validator
        .validate()
        .get_graph_documents()
    )

    # ------------------------------------------------------
    # Statistics
    # ------------------------------------------------------
    total_entities = sum(
        len(g.entities)
        for g in validated_graph
    )

    total_relationships = sum(
        len(g.relationships)
        for g in validated_graph
    )

    print()
    print("-" * 80)
    print("Validation Summary")
    print("-" * 80)

    print(f"Chunks               : {len(validated_graph)}")
    print(f"Entities             : {total_entities}")
    print(f"Relationships        : {total_relationships}")

    # ------------------------------------------------------
    # Save
    # ------------------------------------------------------
    save_graph_documents(
        validated_graph,
        OUTPUT_FILE
    )

    print("\nValidation completed successfully.")


if __name__ == "__main__":
    main()