"""
conftest.py

Adds src/ingestion to sys.path so tests can `import L01_chunking`,
`import schemas`, etc. directly — matching how the modules import each
other (flat, L01_ convention) rather than as a nested package.
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src" / "ingestion"
sys.path.insert(0, str(SRC_DIR))
