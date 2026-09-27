# R01_graph_schema.py

from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

GRAPH_SCHEMA_FILE = "graph_schema.md"

class GraphSchemaExtractor:
    """
    Extracts a rich graph schema from Neo4j suitable for GraphRAG.
    """

    def __init__(self, driver):
        self.driver = driver
        self.database = os.getenv("NEO4J_DATABASE")

    # Public API
    def get_schema(self) -> str:
        """
        Returns a formatted schema description for LLM prompting.
        """

        labels = self.get_node_labels()
        properties = self.get_node_properties(labels)
        relationships = self.get_relationship_schema()
        examples = self.get_node_examples(labels)

        lines = []

        lines.append("=" * 70)
        lines.append("NODE LABELS")
        lines.append("=" * 70)

        for label in labels:

            lines.append(f"\n{label}")

            lines.append("Properties:")

            for prop in properties[label]:
                lines.append(f"  • {prop}")

            if examples[label]:

                lines.append("Examples:")

                for example in examples[label]:
                    lines.append(f"  • {example}")

        lines.append("\n")
        lines.append("=" * 70)
        lines.append("RELATIONSHIPS")
        lines.append("=" * 70)

        for rel in relationships:

            lines.append(
                f"({rel['source']})"
                f"-[:{rel['type']}]->"
                f"({rel['target']})"
            )

        return "\n".join(lines)

    # Labels
    def get_node_labels(self):

        query = """
        CALL db.labels()
        """

        with self.driver.session(database=self.database) as session:

            result = session.run(query)

            return sorted(
                record["label"]
                for record in result
            )

    # Properties
    def get_node_properties(self, labels):

        properties = {}

        with self.driver.session(database=self.database) as session:

            for label in labels:

                query = f"""
                MATCH (n:`{label}`)
                RETURN keys(n) AS props
                LIMIT 1
                """

                result = session.run(query).single()

                if result:
                    properties[label] = sorted(result["props"])
                else:
                    properties[label] = []

        return properties

    # Relationship Schema
    def get_relationship_schema(self):

        query = """
        MATCH (a)-[r]->(b)

        RETURN DISTINCT

            labels(a)[0] AS source,
            type(r) AS relationship,
            labels(b)[0] AS target

        ORDER BY relationship
        """

        schema = []

        with self.driver.session(database=self.database) as session:

            result = session.run(query)

            for row in result:

                schema.append(
                    {
                        "source": row["source"],
                        "type": row["relationship"],
                        "target": row["target"],
                    }
                )

        return schema

    # Example Nodes
    def get_node_examples(self, labels, limit=3):

        examples = {}

        with self.driver.session(database=self.database) as session:
            for label in labels:
                query = f"""
                MATCH (n:`{label}`)
                RETURN n.name AS name
                LIMIT {limit}
                """

                result = session.run(query)

                names = [
                    record["name"]
                    for record in result
                    if record["name"] is not None
                ]

                examples[label] = names

        return examples
    
    def save_schema( self,filepath: str=GRAPH_SCHEMA_FILE ) -> None:
        """
        Extract schema from Neo4j and save it to disk.

        Parameters
        ----------
        filepath : str
            Output file.
        """

        schema = self.get_schema()

        Path(filepath).write_text(
            schema,
            encoding="utf-8"
        )

        print(f"Schema saved to {filepath}")
        
        
    @staticmethod
    def load_schema(filepath: str = GRAPH_SCHEMA_FILE ) -> str:
            """
            Load schema from disk.
            """
            return Path(filepath).read_text(encoding="utf-8")
            


# Example
if __name__ == "__main__":

    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(
            os.getenv("NEO4J_USERNAME"),
            os.getenv("NEO4J_PASSWORD"),
        ),
    )

    extractor = GraphSchemaExtractor(driver)

    extractor.save_schema(GRAPH_SCHEMA_FILE)

    driver.close()