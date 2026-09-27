"""
Factory for the LangChain chat model used for field extraction.
Kept separate from prompt/extraction logic so the underlying provider
(Azure OpenAI today) can be swapped without touching either.
"""
from langchain_openai import ChatOpenAI

from app import config


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=config.AZURE_OPENAI_DEPLOYMENT,
        api_key=config.AZURE_OPENAI_KEY,
        base_url=config.AZURE_OPENAI_ENDPOINT,
        temperature=0,
    )
