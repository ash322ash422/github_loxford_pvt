"""
CLI for GraphRAG
"""

from pprint import pprint

from R06_graph_rag_service import GraphRAGService


def main():

    service = GraphRAGService()

    print("=" * 80)
    print("GRAPH RAG")
    print("=" * 80)

    try:

        while True:

            question = input("\nQuestion ('q' to quit): ")

            if question.lower() in {
                "q",
                "quit",
                "exit",
            }:
                break

            result = service.ask(question)

            print("\n")
            print("=" * 80)
            print("Generated Cypher")
            print("=" * 80)

            print(result["cypher"])

            print("\n")
            print("=" * 80)
            print("Retrieved Graph")
            print("=" * 80)

            pprint(result["graph_data"])

            print("\n")
            print("=" * 80)
            print("Answer")
            print("=" * 80)

            print(result["answer"])

            print("\nConfidence:", result["confidence"])

    finally:

        service.close()


if __name__ == "__main__":

    main()
    
    
# Question 1: Who manages Bob ?   --> Answer is Alice
# Question 2: Which organizations is Bob associated with ?  --> Answer is TechAssociation
# Question 3: How is Alice connected to Diana ?  --> Alice is connected to Diana through TechHub: Alice is CEO_OF TechHub, and Diana WORKS_AT TechHub.


"""
================================================================================
GRAPH RAG
================================================================================

Question ('q' to quit): Who manages Bob ?


================================================================================
Generated Cypher
================================================================================
MATCH (manager:Person)-[:MANAGES]->(:Person {name: "Bob"}) RETURN manager.name AS manager


================================================================================
Retrieved Graph
================================================================================
[{'manager': 'Alice'}]


================================================================================
Answer
================================================================================
Alice

Confidence: 0.9

Question ('q' to quit): Which organizations is Bob associated with ?


================================================================================
Generated Cypher
================================================================================
MATCH (p:Person {name: 'Bob'})-[:CEO_OF|MANAGES|MEMBER_OF|WORKS_AT]->(o:Organization)
RETURN DISTINCT o


================================================================================
Retrieved Graph
================================================================================
[{'o': {'labels': ['Organization'],
        'properties': {'id': 'organization_techassociation',
                       'name': 'TechAssociation'}}}]


================================================================================
Answer
================================================================================
I could not find that information in the graph.

Confidence: 0.1

Question ('q' to quit): How is Alice connected to Diana ?


================================================================================
Generated Cypher
================================================================================
MATCH (a:Person {name: 'Alice'}), (d:Person {name: 'Diana'}) MATCH p = shortestPath((a)-[:CEO_OF|CO_ORGANIZES_WITH|DEVELOPED|FOLLOWS|INTERACTS_WITH|MAINTAINS_PROFILE_ON|MANAGES|MARRIED_TO|MEMBER_OF|ORGANIZES|SHARES_OFFICE_WITH|USES_PLATFORM|VIEWS_POSTS|WORKS_AT|WORKS_ON*1..10]-(d)) RETURN p


================================================================================
Retrieved Graph
================================================================================
[{'p': {'nodes': [{'labels': ['Person'],
                   'properties': {'id': 'person_alice', 'name': 'Alice'}},
                  {'labels': ['Organization'],
                   'properties': {'id': 'organization_techhub',
                                  'name': 'TechHub'}},
                  {'labels': ['Person'],
                   'properties': {'id': 'person_diana', 'name': 'Diana'}}],
        'relationships': [{'properties': {}, 'type': 'CEO_OF'},
                          {'properties': {}, 'type': 'WORKS_AT'}]}}]


================================================================================
Answer
================================================================================
Alice is connected to Diana through TechHub: Alice is CEO_OF TechHub, and Diana WORKS_AT TechHub.

Confidence: 0.88

Question ('q' to quit): q
"""