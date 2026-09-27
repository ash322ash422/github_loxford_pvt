"""
config/settings.py

Centralized configuration, loaded from environment variables (see
.env.example). Importing this module has no side effects other than
reading os.environ — safe to import in tests.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    # OpenAI / extraction
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    extraction_model: str = field(default_factory=lambda: os.getenv("EXTRACTION_MODEL", "gpt-5"))

    # Neo4j
    neo4j_uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", ""))
    neo4j_username: str = field(default_factory=lambda: os.getenv("NEO4J_USERNAME", ""))
    neo4j_password: str = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", ""))
    neo4j_database: str = field(default_factory=lambda: os.getenv("NEO4J_DATABASE", "neo4j"))

    # Pipeline
    chunk_size: int = field(default_factory=lambda: int(os.getenv("CHUNK_SIZE", "600")))
    chunk_overlap: int = field(default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "20")))
    neo4j_batch_size: int = field(default_factory=lambda: int(os.getenv("NEO4J_BATCH_SIZE", "500")))
    entity_similarity_threshold: float = field(
        default_factory=lambda: float(os.getenv("ENTITY_SIMILARITY_THRESHOLD", "0.86"))
    )


settings = Settings()
