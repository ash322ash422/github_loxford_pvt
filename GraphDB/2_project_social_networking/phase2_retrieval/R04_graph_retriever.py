"""
Graph Retriever

Executes validated Cypher queries against Neo4j
and returns structured graph data.
"""

import os

from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.graph import Node, Relationship, Path

load_dotenv()


class GraphRetriever:
    """
    Executes Cypher against Neo4j.
    """

    ####################################################################
    # Initialization
    ####################################################################

    def __init__(self):

        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(
                os.getenv("NEO4J_USERNAME"),
                os.getenv("NEO4J_PASSWORD"),
            ),
        )

        self.database = os.getenv("NEO4J_DATABASE")

    ####################################################################
    # Close Driver
    ####################################################################

    def close(self):

        self.driver.close()

    ####################################################################
    # Validate Query (EXPLAIN)
    ####################################################################

    def explain(self, cypher: str):
        """
        Uses EXPLAIN to verify the Cypher
        before executing it.
        """

        explain_query = "EXPLAIN\n" + cypher

        with self.driver.session(database=self.database) as session:

            session.run(explain_query).consume()

    # from neo4j.graph import Node, Relationship, Path


    def _serialize_value(self, value):
        """
        Recursively serialize Neo4j values into JSON-compatible objects.
        """

        if isinstance(value, Node):
            return {
                "labels": list(value.labels),
                "properties": dict(value),
            }

        elif isinstance(value, Relationship):
            return {
                "type": value.type,
                "properties": dict(value),
            }

        elif isinstance(value, Path):
            return {
                "nodes": [
                    self._serialize_value(node)
                    for node in value.nodes
                ],
                "relationships": [
                    self._serialize_value(rel)
                    for rel in value.relationships
                ],
            }

        elif isinstance(value, list):
            return [
                self._serialize_value(v)
                for v in value
            ]

        elif isinstance(value, dict):
            return {
                k: self._serialize_value(v)
                for k, v in value.items()
            }

        else:
            return value



    ####################################################################
    # Execute Query
    ####################################################################

    def retrieve(self, cypher: str):
        """
        Execute Cypher and return results.
        """

        # --------------------------------------------------------------
        # First validate query using Neo4j planner
        # --------------------------------------------------------------

        self.explain(cypher)

        # --------------------------------------------------------------
        # Execute
        # --------------------------------------------------------------

        with self.driver.session(database=self.database) as session:

            result = session.run(cypher)

            records = []

            for record in result:

                row = {}

                for key in record.keys():
                    row[key] = self._serialize_value(record[key])

                records.append(row)

            return records



        return records


###########################################################################
# Example
###########################################################################

if __name__ == "__main__":

    retriever = GraphRetriever()

    cypher = """
    MATCH (p:Person)-[:MANAGES]->(b:Person)
    WHERE b.name = "Bob"
    RETURN p
    """
    
    # cypher = """
    # MATCH p = shortestPath(
    #     (a:Person {name:"Alice"})-[*]-(d:Person {name:"Diana"})
    # )
    # RETURN p
    # """


    data = retriever.retrieve(cypher)

    print("=" * 80)
    print("Retrieved Data")
    print("=" * 80)

    from pprint import pprint

    pprint(data)

    retriever.close()
    
    
    
# ================================================================================
# Retrieved Data
# ================================================================================
# [{'p': {'labels': ['Person'],
#         'properties': {'id': 'person_alice', 'name': 'Alice'}}}]
    
    
    