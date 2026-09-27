from typing import List
from pydantic import BaseModel, Field


class Entity(BaseModel):
    """    Graph Node    """

    id: str = Field(description="Unique identifier for the entity.")
    name: str = Field(description="Entity name." )
    label: str = Field(
        description="Entity type like Person, Organization, Product, Platform."
    )


class Relationship(BaseModel):
    """   Graph Edge    """

    source: str = Field(description="Source entity id.")
    target: str = Field(description="Target entity id.")
    relation: str = Field(description="Relationship type.")


class GraphDocument(BaseModel):
    chunk_id: int
    entities: List[Entity]
    relationships: List[Relationship]    



class CanonicalGraph(BaseModel):
    """
    Final graph after validation.

    Contains unique entities and relationships.
    """

    entities: List[Entity]
    relationships: List[Relationship]