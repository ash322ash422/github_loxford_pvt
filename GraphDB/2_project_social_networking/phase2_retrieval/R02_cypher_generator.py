# R02_cypher_generator.py
"""
Generates Cypher from natural language.

Input
-----
Natural language question

Output
------
CypherQuery
"""

import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from schema_store import SchemaStore
load_dotenv()

GRAPH_SCHEMA_FILE = "graph_schema.md"
MODEL = "gpt-5"

###########################################################################
# Structured Output
###########################################################################

class CypherQuery(BaseModel):
    """
    LLM output.
    """

    cypher: str = Field(
        description="Valid Cypher query."
    )

    reason: str = Field(
        description="Reason for generating the query."
    )


###########################################################################
# Prompt
###########################################################################

PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are an expert Neo4j Cypher engineer.

Your task is to convert a user's question into a valid Cypher query.

-------------------------------------------------------
Rules
-------------------------------------------------------

1. Use ONLY the schema provided.

2. Never invent node labels.

3. Never invent relationship names.

4. Never invent properties.

5. Use MATCH.

6. Use node property 'name' when filtering.

7. Do NOT use APOC.

8. Return exactly ONE Cypher query.

9. Do NOT explain the query.

10. If the question cannot be answered using
the schema, return

MATCH (n)
RETURN "I don't know"
LIMIT 1

-------------------------------------------------------
Schema
-------------------------------------------------------

{schema}

"""
        ),
        (
            "human",
            "{question}"
        )
    ]
)


###########################################################################
# Cypher Generator
###########################################################################

class CypherGenerator:

    def __init__(
        self,
        schema_file: str = GRAPH_SCHEMA_FILE,
        model: str = MODEL
    ):

        # Load cached schema
        self.schema = SchemaStore(schema_file).get_schema()

        # LLM
        llm = ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=model,
            temperature=0,
        )

        # Chain
        self.chain = (
            PROMPT  | llm.with_structured_output( CypherQuery )
        )

    def generate( self, question: str ) -> CypherQuery:
        """
        Generate Cypher.
        """

        return self.chain.invoke(
            {
                "schema": self.schema,
                "question": question,
            }
        )


# Example
if __name__ == "__main__":

    generator = CypherGenerator()

    result = generator.generate( "Who manages Bob?" )

    print("=" * 80)
    print("Generated Cypher")
    print("=" * 80)

    print()

    print(result.cypher)

    print()

    print("=" * 80)
    print("Reason")
    print("=" * 80)

    print()

    print(result.reason)
    
""" OUTPUT
# ================================================================================
# Generated Cypher
# ================================================================================

# MATCH (manager:Person)-[:MANAGES]->(bob:Person {name: 'Bob'}) RETURN manager.name AS manager

# ================================================================================
# Reason
# ================================================================================

# Find persons who manage Bob via the MANAGES relationship.
"""