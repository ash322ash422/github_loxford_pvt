# neo4j_loader.py

import os
from typing import List

from dotenv import load_dotenv
from neo4j import GraphDatabase

from schemas import Entity, Relationship

load_dotenv()

class Neo4jGraphLoader:
    """
    Production-ready Neo4j graph loader.

    Responsibilities
    ----------------
    1. Connect to Neo4j
    2. Create uniqueness constraints
    3. Load nodes
    4. Load relationships
    5. Verify graph
    6. Close connection
    """

    ####################################################################
    # Constructor
    ####################################################################

    def __init__(
        self,
        uri: str = None,
        username: str = None,
        password: str = None,
    ):

        self.uri = uri or os.getenv("NEO4J_URI")
        self.username = username or os.getenv("NEO4J_USERNAME")
        self.password = password or os.getenv("NEO4J_PASSWORD")

        self.driver = None

    ####################################################################
    # Connection
    ####################################################################

    def connect(self):
        """
        Connect to Neo4j.
        """

        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password),
        )

        self.driver.verify_connectivity()

        print("Connected to Neo4j.")

    ####################################################################
    # Close
    ####################################################################

    def close(self):

        if self.driver:
            self.driver.close()
            print("Neo4j connection closed.")

    ####################################################################
    # Constraints
    ####################################################################

    def create_constraints(self):
        """
        Create uniqueness constraints.
        """

        labels = [
            "Person",
            "Organization",
            "Product",
            "Platform",
            "Group",
        ]

        with self.driver.session() as session:

            for label in labels:

                cypher = f"""
                CREATE CONSTRAINT {label.lower()}_id_unique
                IF NOT EXISTS

                FOR (n:{label})

                REQUIRE n.id IS UNIQUE
                """

                session.run(cypher)

        print("Constraints created.")

    ####################################################################
    # Load Nodes
    ####################################################################

    def load_entities(
        self,
        entities: List[Entity],
    ):
        """
        Insert all graph nodes.
        """

        with self.driver.session() as session:

            for entity in entities:

                session.execute_write(
                    self._create_entity,
                    entity,
                )

        print(f"Loaded {len(entities)} entities.")

    @staticmethod
    def _create_entity(tx, entity: Entity):

        cypher = f"""
        MERGE (n:{entity.label} {{id:$id}})

        SET
            n.name=$name
        """

        tx.run(
            cypher,
            id=entity.id,
            name=entity.name,
        )

    ####################################################################
    # Load Relationships
    ####################################################################

    def load_relationships(
        self,
        relationships: List[Relationship],
    ):
        """
        Insert graph relationships.
        """

        with self.driver.session() as session:

            for relationship in relationships:

                session.execute_write(
                    self._create_relationship,
                    relationship,
                )

        print(f"Loaded {len(relationships)} relationships.")

    @staticmethod
    def _create_relationship(tx, relationship: Relationship):

        cypher = f"""
        MATCH (a {{id:$source}})
        MATCH (b {{id:$target}})

        MERGE (a)-[r:{relationship.relation}]->(b)
        """

        tx.run(
            cypher,
            source=relationship.source,
            target=relationship.target,
        )

    ####################################################################
    # Verification
    ####################################################################

    def count_nodes(self):

        with self.driver.session() as session:

            result = session.run(
                """
                MATCH (n)

                RETURN count(n) AS count
                """
            )

            return result.single()["count"]

    def count_relationships(self):

        with self.driver.session() as session:

            result = session.run(
                """
                MATCH ()-[r]->()

                RETURN count(r) AS count
                """
            )

            return result.single()["count"]

    ####################################################################
    # Graph Summary
    ####################################################################

    def verify_graph(self):

        nodes = self.count_nodes()

        relationships = self.count_relationships()

        print("\nGraph Summary")
        print("-" * 40)

        print(f"Nodes          : {nodes}")
        print(f"Relationships  : {relationships}")