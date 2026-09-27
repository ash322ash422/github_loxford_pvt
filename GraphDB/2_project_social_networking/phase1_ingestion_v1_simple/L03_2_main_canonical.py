import json

from schemas import (
    GraphDocument,
    CanonicalGraph,
)


INPUT_FILE = "L03_validated_graph.json"
OUTPUT_FILE = "L03_canonical_graph.json"


# Load validated graph
def load_graph_documents(filename):

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [
        GraphDocument.model_validate(item)
        for item in data
    ]


# Build Canonical Graph
def build_canonical_graph(graph_documents):

    entity_map = {}

    relationship_map = {}

    # Merge Entities
    for graph in graph_documents:
        for entity in graph.entities:
            entity_map[entity.id] = entity

    # Merge Relationships
    for graph in graph_documents:
        for rel in graph.relationships:
            key = (
                rel.source,
                rel.target,
                rel.relation,
            )

            relationship_map[key] = rel

    return CanonicalGraph(
        entities=list(entity_map.values()),
        relationships=list(relationship_map.values())
    )


# Save
def save_canonical_graph(graph, filename):

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            graph.model_dump(mode="json"),
            f,
            indent=4,
            ensure_ascii=False,
        )

    print(f"\nSaved canonical graph -> {filename}")


# Main
def main():

    print("=" * 80)
    print("BUILDING CANONICAL GRAPH")
    print("=" * 80)

    graph_documents = load_graph_documents(INPUT_FILE)
    graph = build_canonical_graph(graph_documents)
    print()

    print(f"Unique Entities      : {len(graph.entities)}")
    print(f"Unique Relationships : {len(graph.relationships)}")

    save_canonical_graph(
        graph,
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()