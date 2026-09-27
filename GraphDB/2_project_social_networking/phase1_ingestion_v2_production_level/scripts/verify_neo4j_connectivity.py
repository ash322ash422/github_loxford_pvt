#!/usr/bin/env python3
"""
scripts/verify_neo4j_connectivity.py

Quick standalone check that NEO4J_URI/USERNAME/PASSWORD in .env are
correct and the instance is reachable, before running the full pipeline.

Usage: python scripts/verify_neo4j_connectivity.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "ingestion"))

from L04_neo4j_loader import Neo4jGraphLoader

if __name__ == "__main__":
    with Neo4jGraphLoader() as loader:
        print("Connection successful!")
        print(loader.verify_graph())
