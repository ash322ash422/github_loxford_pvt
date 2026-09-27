"""
Step 4 : Neo4j Graph Ingestion

Reads the final Knowledge Graph JSON and loads it into Neo4j.
"""

import json

from schemas import CanonicalGraph
from L04_neo4j_loader import Neo4jGraphLoader

# Configuration
INPUT_FILE = "L03_canonical_graph.json"

# Load Knowledge Graph
def load_knowledge_graph(filename: str) -> CanonicalGraph:
    """
    Load the canonical knowledge graph from JSON.
    """

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph = CanonicalGraph.model_validate(data)

    print(f"Knowledge graph loaded from: {filename}")

    return graph


# Main
def main():

    print("=" * 80)
    print("STEP 4 : NEO4J GRAPH INGESTION")
    print("=" * 80)

    # Load Knowledge Graph
    graph = load_knowledge_graph(INPUT_FILE)

    print()
    print(f"Entities      : {len(graph.entities)}")
    print(f"Relationships : {len(graph.relationships)}")
    print()

    loader = Neo4jGraphLoader()

    try:
        # Connect
        loader.connect()

        # Create Constraints
        loader.create_constraints()

        # Load Nodes
        print("\nLoading entities...")
        loader.load_entities(graph.entities)

        # Load Relationships
        print("\nLoading relationships...")
        loader.load_relationships(graph.relationships)

        # Verify
        print("\nVerifying graph...")
        loader.verify_graph()

    finally:
        loader.close()


# Entry Point
if __name__ == "__main__":
    main()