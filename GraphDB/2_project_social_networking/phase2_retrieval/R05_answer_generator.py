# R05_answer_generator.py

"""
Converts retrieved graph data into a natural language answer.
"""

import os
import json

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


load_dotenv()

MODEL = "gpt-5"

##############################################################################
# Output Schema
##############################################################################

class Answer(BaseModel):
    """
    Final answer returned to the user.
    """

    answer: str = Field(
        description="Natural language answer."
    )

    confidence: float = Field(
        description="Confidence score between 0 and 1."
    )


##############################################################################
# Prompt
##############################################################################

PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are an expert graph question answering assistant.

            You are given:

            1. The user's question.
            2. Data retrieved from a Neo4j graph.

            Rules

            1. Answer ONLY using the retrieved data.

            2. Never hallucinate.

            3. If the answer cannot be found,
            respond with:

            "I could not find that information in the graph."

            4. Keep the answer concise.

            5. Mention names exactly as they appear.

            6. Do not mention Cypher or Neo4j.
            
            7. Provide a confidence score between 0 and 1.

            """
        ),
        (
            "human",
            """
                Question

                {question}

                Retrieved Graph Data

                {graph_data}
            """
        )
    ]
)


##############################################################################
# Answer Generator
##############################################################################

class AnswerGenerator:

    def __init__(self):

        llm = ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=MODEL,
            temperature=0
        )

        self.chain = (PROMPT | llm.with_structured_output(Answer))

    ##########################################################################

    def generate( self, question: str, graph_data) -> Answer:
        """
        Generate final answer.
        """

        return self.chain.invoke(
            {
                "question": question,
                "graph_data": json.dumps(
                    graph_data,
                    indent=2
                )
            }
        )


##############################################################################
# Example
##############################################################################

if __name__ == "__main__":

    graph_data = [
        {
            "manager": "Alice"
        }
    ]

    generator = AnswerGenerator()

    answer = generator.generate(
        question="Who manages Bob?",
        graph_data=graph_data
    )

    print("=" * 80)
    print("Answer")
    print("=" * 80)

    print()

    print(answer.answer)

    print()

    print("Confidence:", answer.confidence)