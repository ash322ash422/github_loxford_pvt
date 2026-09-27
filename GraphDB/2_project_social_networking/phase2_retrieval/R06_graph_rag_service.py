# R06_graph_rag_service.py

"""
Production GraphRAG Service.

This class orchestrates the complete GraphRAG pipeline.

It contains no UI code.

It can be reused by

• app.py
• FastAPI
• Streamlit
• LangGraph
• Unit Tests
"""

from R02_cypher_generator import CypherGenerator
from R03_cypher_validator import CypherValidator
from R04_graph_retriever import GraphRetriever
from R05_answer_generator import AnswerGenerator


class GraphRAGService:

    ####################################################################
    # Initialization
    ####################################################################

    def __init__(self):

        self.cypher_generator = CypherGenerator()

        self.cypher_validator = CypherValidator()

        self.graph_retriever = GraphRetriever()

        self.answer_generator = AnswerGenerator()

    ####################################################################
    # Public API
    ####################################################################

    def ask(self, question: str) -> dict:
        """
        Complete GraphRAG pipeline.

        Parameters
        ----------
        question : str

        Returns
        -------
        dict
        """

        ###############################################################
        # Step 1
        ###############################################################

        cypher_result = self.cypher_generator.generate(  question )

        ###############################################################
        # Step 2
        ###############################################################

        self.cypher_validator.validate(cypher_result.cypher )

        ###############################################################
        # Step 3
        ###############################################################

        graph_data = self.graph_retriever.retrieve( cypher_result.cypher)
        ###############################################################
        # Step 4
        ###############################################################

        answer = self.answer_generator.generate(
            question=question,
            graph_data=graph_data,
        )

        ###############################################################
        # Final Result
        ###############################################################

        return {
            "question": question,
            "cypher": cypher_result.cypher,
            "reason": cypher_result.reason,
            "graph_data": graph_data,
            "answer": answer.answer,
            "confidence": answer.confidence,
        }

    ####################################################################
    # Cleanup
    ####################################################################

    def close(self):
        self.graph_retriever.close()