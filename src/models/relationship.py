"""
Relationship Models
===================

Defines models for relationships between code entities.
These represent the "edges" in our knowledge graph.

HOW IT WORKS:
    1. CodeQL analysis identifies relationships between entities
    2. Each relationship becomes a Relationship object
    3. Relationships are stored in Neo4j as edges between nodes
    4. Impact analysis uses these relationships to trace dependencies

RELATIONSHIP TYPES:
    - CALLS: Function A calls Function B
    - IMPORTS: Module A imports from Module B
    - INHERITS: Class A inherits from Class B
    - USES: Entity A uses Entity B
    - CONTAINS: Module/Class contains Functions/Methods
    - DECORATES: Decorator A decorates Function/Class B
    - RETURNS: Function returns Type/Class
    - RAISES: Function raises Exception

DATA FLOW:
    Source Code Analysis
           ↓
    Identify Relationships
           ↓
    Relationship Objects
           ↓
    Neo4j Edges (relationships)

VISUAL EXAMPLE:
    ┌──────────────┐  CALLS   ┌──────────────┐
    │ process_data │─────────►│ validate     │
    └──────────────┘          └──────────────┘
           │
           │ USES
           ▼
    ┌──────────────┐
    │ DataModel    │
    └──────────────┘

USAGE:
    from src.models.relationship import Relationship, RelationshipType

    # Create a relationship
    rel = Relationship(
        source_id=func_a.id,
        target_id=func_b.id,
        relationship_type=RelationshipType.CALLS,
        metadata={"line": 42}
    )
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RelationshipType(str, Enum):
    """
    Types of relationships between code entities.

    These map to different edge types in the Neo4j knowledge graph.
    Each relationship type has semantic meaning for impact analysis.
    """

    # Function Relationships
    CALLS = "calls"              # Function A calls Function B
    CALLED_BY = "called_by"      # Inverse of CALLS

    # Import Relationships
    IMPORTS = "imports"          # Module A imports from Module B
    IMPORTED_BY = "imported_by"  # Inverse of IMPORTS

    # Inheritance Relationships
    INHERITS = "inherits"        # Class A inherits from Class B
    INHERITED_BY = "inherited_by"  # Inverse of INHERITS

    # Usage Relationships
    USES = "uses"                # Entity A uses Entity B
    USED_BY = "used_by"          # Inverse of USES

    # Containment Relationships
    CONTAINS = "contains"        # Module/Class contains Function/Method
    CONTAINED_IN = "contained_in"  # Inverse of CONTAINS

    # Decorator Relationships
    DECORATES = "decorates"      # Decorator A decorates Entity B
    DECORATED_BY = "decorated_by"  # Inverse of DECORATES

    # Type Relationships
    RETURNS = "returns"          # Function returns Type/Class
    RETURNED_BY = "returned_by"  # Inverse of RETURNS
    ACCEPTS = "accepts"          # Function accepts Type as parameter
    PARAMETER_OF = "parameter_of"  # Inverse of ACCEPTS

    # Exception Relationships
    RAISES = "raises"            # Function raises Exception
    RAISED_BY = "raised_by"      # Inverse of RAISES

    # Override Relationships
    OVERRIDES = "overrides"      # Method overrides parent method
    OVERRIDDEN_BY = "overridden_by"  # Inverse of OVERRIDES


# Mapping of relationships to their inverse
INVERSE_RELATIONSHIPS: dict[RelationshipType, RelationshipType] = {
    RelationshipType.CALLS: RelationshipType.CALLED_BY,
    RelationshipType.CALLED_BY: RelationshipType.CALLS,
    RelationshipType.IMPORTS: RelationshipType.IMPORTED_BY,
    RelationshipType.IMPORTED_BY: RelationshipType.IMPORTS,
    RelationshipType.INHERITS: RelationshipType.INHERITED_BY,
    RelationshipType.INHERITED_BY: RelationshipType.INHERITS,
    RelationshipType.USES: RelationshipType.USED_BY,
    RelationshipType.USED_BY: RelationshipType.USES,
    RelationshipType.CONTAINS: RelationshipType.CONTAINED_IN,
    RelationshipType.CONTAINED_IN: RelationshipType.CONTAINS,
    RelationshipType.DECORATES: RelationshipType.DECORATED_BY,
    RelationshipType.DECORATED_BY: RelationshipType.DECORATES,
    RelationshipType.RETURNS: RelationshipType.RETURNED_BY,
    RelationshipType.RETURNED_BY: RelationshipType.RETURNS,
    RelationshipType.ACCEPTS: RelationshipType.PARAMETER_OF,
    RelationshipType.PARAMETER_OF: RelationshipType.ACCEPTS,
    RelationshipType.RAISES: RelationshipType.RAISED_BY,
    RelationshipType.RAISED_BY: RelationshipType.RAISES,
    RelationshipType.OVERRIDES: RelationshipType.OVERRIDDEN_BY,
    RelationshipType.OVERRIDDEN_BY: RelationshipType.OVERRIDES,
}


class Relationship(BaseModel):
    """
    Represents a relationship (edge) between two code entities.

    A relationship connects a source entity to a target entity
    with a specific type that describes how they are related.

    Attributes:
        id: Unique identifier for this relationship
        source_id: UUID of the source entity (start of the edge)
        target_id: UUID of the target entity (end of the edge)
        relationship_type: Type of relationship (CALLS, IMPORTS, etc.)
        weight: Strength/importance of the relationship (1.0 = normal)
        file_path: File where this relationship was found
        line_number: Line number where the relationship occurs
        metadata: Additional context about the relationship
        created_at: When this relationship was first identified
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this relationship"
    )
    source_id: UUID = Field(
        description="UUID of the source entity"
    )
    target_id: UUID = Field(
        description="UUID of the target entity"
    )
    relationship_type: RelationshipType = Field(
        description="Type of relationship"
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Strength/importance of the relationship"
    )
    file_path: str | None = Field(
        default=None,
        description="File where this relationship was found"
    )
    line_number: int | None = Field(
        default=None,
        ge=1,
        description="Line number where the relationship occurs"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this relationship was identified"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True

    def to_neo4j_properties(self) -> dict[str, Any]:
        """
        Convert relationship to Neo4j edge properties.

        Returns a dictionary suitable for creating a
        Neo4j relationship/edge.

        Returns:
            Dictionary of relationship properties
        """
        return {
            "id": str(self.id),
            "relationship_type": self.relationship_type,
            "weight": self.weight,
            "file_path": self.file_path or "",
            "line_number": self.line_number or 0,
            "created_at": self.created_at.isoformat(),
        }

    def get_inverse(self) -> "Relationship":
        """
        Get the inverse of this relationship.

        Creates a new Relationship with source and target swapped
        and the relationship type inverted.

        Returns:
            New Relationship representing the inverse

        Example:
            A --CALLS--> B  becomes  B --CALLED_BY--> A
        """
        inverse_type = INVERSE_RELATIONSHIPS.get(
            RelationshipType(self.relationship_type),
            RelationshipType.USES  # Default fallback
        )
        return Relationship(
            source_id=self.target_id,
            target_id=self.source_id,
            relationship_type=inverse_type,
            weight=self.weight,
            file_path=self.file_path,
            line_number=self.line_number,
            metadata=self.metadata,
        )


class RelationshipPath(BaseModel):
    """
    Represents a path through multiple relationships.

    Used in impact analysis to show how changes propagate
    through the codebase.

    Example Path:
        process_data --CALLS--> validate --USES--> DataModel

    Attributes:
        relationships: List of relationships forming the path
        total_weight: Sum of all relationship weights
        depth: Number of hops in the path
    """

    relationships: list[Relationship] = Field(
        default_factory=list,
        description="List of relationships forming the path"
    )

    @property
    def total_weight(self) -> float:
        """Calculate total weight of the path."""
        return sum(r.weight for r in self.relationships)

    @property
    def depth(self) -> int:
        """Get the depth (number of hops) in the path."""
        return len(self.relationships)

    @property
    def entity_ids(self) -> list[UUID]:
        """Get all entity IDs in the path (in order)."""
        if not self.relationships:
            return []
        ids = [self.relationships[0].source_id]
        ids.extend(r.target_id for r in self.relationships)
        return ids

    def to_string(self, entity_names: dict[UUID, str]) -> str:
        """
        Convert path to human-readable string.

        Args:
            entity_names: Mapping of entity IDs to names

        Returns:
            String representation like "A --CALLS--> B --USES--> C"
        """
        if not self.relationships:
            return "(empty path)"

        parts = [entity_names.get(self.relationships[0].source_id, "?")]
        for rel in self.relationships:
            parts.append(f" --{rel.relationship_type}--> ")
            parts.append(entity_names.get(rel.target_id, "?"))
        return "".join(parts)
