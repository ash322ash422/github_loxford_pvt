# L03__validation_normalization.py

import re
from copy import deepcopy

VALID_ENTITY_LABELS = {
    "Person",
    "Organization",
    "Product",
    "Platform",
    "Group",
}


SYMMETRIC_RELATIONS = {
    "MARRIED_TO",
    "SHARES_OFFICE_WITH",
    "CO_ORGANIZES_WITH",
    "INTERACTS_WITH"
}

VALID_RELATIONS = {
    "CEO_OF",
    "MANAGES",
    "DEVELOPED",
    "WORKS_AT",
    "WORKS_ON",
    "MARRIED_TO",
    "SHARES_OFFICE_WITH",
    "MEMBER_OF",
    "ORGANIZES",
    "CO_ORGANIZES_WITH",
    "INTERACTS_WITH",
    "FOLLOWS",
    "USES_PLATFORM",
    "MAINTAINS_PROFILE_ON",
    "VIEWS_POSTS"
}

class GraphValidator:
    """
    Performs validation and normalization of GraphDocument objects.
    """

    def __init__(self, graph_documents):
        """
        Parameters
        ----------
        graph_documents : List[GraphDocument]
        """
        self.graph_documents = deepcopy(graph_documents)

    # Rule 1
    def validate_entity_labels(self):
        """
        Remove entities having invalid labels.
        """

        for graph in self.graph_documents:

            graph.entities = [
                entity
                for entity in graph.entities
                if entity.label in VALID_ENTITY_LABELS
            ]

        return self

    # Rule 2
    def normalize_entity_ids(self):
        """
        Normalize entity ids.

        Example

        Person.Alice
                ↓
        person_alice

        Person Alice
                ↓
        person_alice
        """

        for graph in self.graph_documents:
            for entity in graph.entities:
                entity.id = self._normalize_id(entity.id)

        return self

    # Rule 3
    def remove_duplicate_entities(self):
        """
        Remove duplicate entities across all chunks.

        Duplicate means same normalized id.
        """

        unique_entities = {}

        for graph in self.graph_documents:

            new_entities = []
            for entity in graph.entities:
                if entity.id not in unique_entities:
                    unique_entities[entity.id] = entity
                    new_entities.append(entity)

            graph.entities = new_entities

        return self

    # Helper
    @staticmethod
    def _normalize_id(entity_id: str) -> str:
        """
        Normalize entity ids.

        Examples

        Person.Alice
        PERSON ALICE
        person-alice

        ↓

        person_alice
        """
        entity_id = entity_id.lower()
        entity_id = entity_id.replace(".", "_")
        entity_id = entity_id.replace("-", "_")
        entity_id = entity_id.replace(" ", "_")
        entity_id = re.sub(r"_+", "_", entity_id)

        return entity_id


    def remove_duplicate_relationships(self):
        """
        Remove duplicate relationships across all chunks.
        """

        unique = set()

        for graph in self.graph_documents:

            new_relationships = []

            for rel in graph.relationships:

                key = (
                    rel.source,
                    rel.target,
                    rel.relation
                )

                if key not in unique:
                    unique.add(key)
                    new_relationships.append(rel)

            graph.relationships = new_relationships

        return self


    def remove_symmetric_relationships(self):
        """
        Remove duplicate symmetric relationships.

        Example

        Bob MARRIED_TO Charlie
        Charlie MARRIED_TO Bob

        Keep only one.
        """

        for graph in self.graph_documents:

            seen = set()

            new_relationships = []

            for rel in graph.relationships:
                if rel.relation not in SYMMETRIC_RELATIONS:
                    new_relationships.append(rel)
                    continue

                key = tuple(
                    sorted([rel.source, rel.target])
                ) + (rel.relation,)

                if key not in seen:
                    seen.add(key)
                    new_relationships.append(rel)

            graph.relationships = new_relationships

        return self

    def remove_orphan_relationships(self):
        """
        Remove relationships whose source or target
        entity does not exist.
        """

        entity_ids = set()

        for graph in self.graph_documents:

            for entity in graph.entities:

                entity_ids.add(entity.id)

        for graph in self.graph_documents:

            graph.relationships = [

                rel

                for rel in graph.relationships

                if rel.source in entity_ids
                and rel.target in entity_ids

            ]

        return self


    def validate_relationship_types(self):
        """
        Remove relationships having invalid relation names.
        """

        for graph in self.graph_documents:

            graph.relationships = [
                rel
                for rel in graph.relationships if rel.relation in VALID_RELATIONS
            ]

        return self

    def validate(self):
        """
        Run complete validation pipeline.
        """

        return (
            self
            .validate_entity_labels()
            .normalize_entity_ids()
            .remove_duplicate_entities()
            .validate_relationship_types()
            .remove_duplicate_relationships()
            .remove_symmetric_relationships()
            # .remove_generic_entities()
            .remove_orphan_relationships()
        )

    # Getter
    def get_graph_documents(self):
        return self.graph_documents