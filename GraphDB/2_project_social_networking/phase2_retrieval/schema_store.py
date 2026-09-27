"""
Schema Store

Loads and caches the graph schema.

The schema is extracted once from Neo4j and stored
as graph_schema.md.

Every retrieval request simply loads it from here.
"""

from pathlib import Path


class SchemaStore:
    """
    Loads graph schema from disk and caches it.
    """

    def __init__(self, schema_file: str = "graph_schema.md"):

        self.schema_file = Path(schema_file)
        self._schema = None

    def get_schema(self) -> str:
        """
        Returns cached schema.

        Reads from disk only once.
        """

        if self._schema is None:

            self._schema = self.schema_file.read_text(
                encoding="utf-8"
            )

        return self._schema

    def refresh(self) -> str:
        """
        Reload schema from disk.
        """

        self._schema = self.schema_file.read_text(
            encoding="utf-8"
        )

        return self._schema