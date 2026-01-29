"""
Impact Analysis Models
======================

Defines models for impact analysis results.
These represent the output of analyzing how changes propagate.

HOW IT WORKS:
    1. User specifies a code entity or change to analyze
    2. System traverses the knowledge graph from that entity
    3. Identifies all entities that could be affected
    4. Ranks impacts by severity and distance
    5. Returns structured impact analysis results

IMPACT LEVELS:
    - DIRECT: Immediately affected (1 hop away)
    - INDIRECT: Affected through chain (2-3 hops)
    - POTENTIAL: Might be affected (distant relationship)

DATA FLOW:
    Changed Entity (input)
           ↓
    Neo4j Graph Traversal
           ↓
    Find All Connected Entities
           ↓
    Calculate Impact Scores
           ↓
    ImpactAnalysis Result

VISUAL EXAMPLE:
    If we change function `validate_input`:

                            ┌─────────────────┐
                            │ validate_input  │ ◄── CHANGED
                            └────────┬────────┘
                    DIRECT           │
              ┌──────────────────────┼──────────────────┐
              ↓                      ↓                  ↓
    ┌─────────────────┐    ┌─────────────────┐   ┌──────────────┐
    │ process_data    │    │ handle_request  │   │ parse_form   │
    └────────┬────────┘    └────────┬────────┘   └──────────────┘
    INDIRECT │                      │
             ↓                      ↓
    ┌─────────────────┐    ┌─────────────────┐
    │ export_results  │    │ api_endpoint    │
    └─────────────────┘    └─────────────────┘

USAGE:
    from src.models.impact import ImpactAnalysis, ImpactLevel

    # Impact analysis result
    analysis = ImpactAnalysis(
        source_entity_id=func_id,
        impacted_entities=[...],
        total_impact_score=8.5
    )
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.models.code_entity import CodeEntityType


class ImpactLevel(str, Enum):
    """
    Levels of impact severity.

    Used to categorize how directly an entity is affected.
    """

    CRITICAL = "critical"    # Breaking change, requires immediate attention
    DIRECT = "direct"        # Directly affected (1 hop)
    INDIRECT = "indirect"    # Indirectly affected (2-3 hops)
    POTENTIAL = "potential"  # Potentially affected (distant)
    MINIMAL = "minimal"      # Very unlikely to be affected


class ImpactCategory(str, Enum):
    """
    Categories of impact for grouping.

    Helps organize impact results by type.
    """

    FUNCTIONALITY = "functionality"  # Affects behavior/logic
    API = "api"                      # Affects public interfaces
    DATA = "data"                    # Affects data handling
    PERFORMANCE = "performance"      # Affects performance
    SECURITY = "security"            # Affects security
    TESTING = "testing"              # Affects tests


class ImpactedEntity(BaseModel):
    """
    Represents an entity that could be impacted by a change.

    Includes information about the entity and the nature
    of the potential impact.

    Attributes:
        entity_id: UUID of the impacted entity
        entity_name: Name of the entity
        entity_type: Type of entity (function, class, etc.)
        file_path: File containing the entity
        impact_level: How severe the impact is
        impact_score: Numeric score (0-10) for ranking
        distance: Number of hops from the source entity
        relationship_path: How this entity is connected to source
        reason: Human-readable explanation of why it's impacted
        categories: Types of impact (functionality, API, etc.)
        suggested_action: Recommended action to take
    """

    entity_id: UUID = Field(
        description="UUID of the impacted entity"
    )
    entity_name: str = Field(
        description="Name of the entity"
    )
    entity_type: CodeEntityType = Field(
        description="Type of entity"
    )
    file_path: str = Field(
        description="File containing the entity"
    )
    impact_level: ImpactLevel = Field(
        description="Severity of the impact"
    )
    impact_score: float = Field(
        ge=0.0,
        le=10.0,
        description="Numeric impact score for ranking"
    )
    distance: int = Field(
        ge=1,
        description="Number of hops from source entity"
    )
    relationship_path: list[str] = Field(
        default_factory=list,
        description="Relationship types in the path"
    )
    reason: str = Field(
        default="",
        description="Why this entity is impacted"
    )
    categories: list[ImpactCategory] = Field(
        default_factory=list,
        description="Types of impact"
    )
    suggested_action: str = Field(
        default="Review for compatibility",
        description="Recommended action"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class ImpactAnalysis(BaseModel):
    """
    Complete impact analysis result.

    Contains all information about the impact of a change,
    including all affected entities and summary statistics.

    Attributes:
        id: Unique identifier for this analysis
        source_entity_id: The entity being changed
        source_entity_name: Name of the source entity
        source_file_path: File containing the source entity
        impacted_entities: List of all impacted entities
        total_impact_score: Sum of all impact scores
        max_depth: Maximum distance of any impacted entity
        summary: Human-readable summary of the analysis
        recommendations: List of recommended actions
        metadata: Additional analysis metadata
        created_at: When the analysis was performed
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier"
    )
    source_entity_id: UUID = Field(
        description="The entity being changed"
    )
    source_entity_name: str = Field(
        description="Name of the source entity"
    )
    source_file_path: str = Field(
        description="File containing the source entity"
    )
    impacted_entities: list[ImpactedEntity] = Field(
        default_factory=list,
        description="All impacted entities"
    )
    total_impact_score: float = Field(
        default=0.0,
        ge=0.0,
        description="Sum of all impact scores"
    )
    max_depth: int = Field(
        default=0,
        ge=0,
        description="Maximum traversal depth"
    )
    summary: str = Field(
        default="",
        description="Human-readable summary"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommended actions"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When analysis was performed"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True

    @property
    def critical_count(self) -> int:
        """Count of critically impacted entities."""
        return sum(
            1 for e in self.impacted_entities
            if e.impact_level == ImpactLevel.CRITICAL
        )

    @property
    def direct_count(self) -> int:
        """Count of directly impacted entities."""
        return sum(
            1 for e in self.impacted_entities
            if e.impact_level == ImpactLevel.DIRECT
        )

    @property
    def indirect_count(self) -> int:
        """Count of indirectly impacted entities."""
        return sum(
            1 for e in self.impacted_entities
            if e.impact_level == ImpactLevel.INDIRECT
        )

    @property
    def total_count(self) -> int:
        """Total count of impacted entities."""
        return len(self.impacted_entities)

    def get_by_level(self, level: ImpactLevel) -> list[ImpactedEntity]:
        """Get all entities at a specific impact level."""
        return [e for e in self.impacted_entities if e.impact_level == level]

    def get_by_file(self, file_path: str) -> list[ImpactedEntity]:
        """Get all impacted entities in a specific file."""
        return [e for e in self.impacted_entities if e.file_path == file_path]

    def generate_summary(self) -> str:
        """
        Generate a human-readable summary of the impact analysis.

        Returns:
            Summary string describing the impact
        """
        parts = [
            f"Impact Analysis for '{self.source_entity_name}'",
            f"in {self.source_file_path}",
            "",
            f"Total impacted entities: {self.total_count}",
            f"  - Critical: {self.critical_count}",
            f"  - Direct: {self.direct_count}",
            f"  - Indirect: {self.indirect_count}",
            f"  - Potential: {len(self.get_by_level(ImpactLevel.POTENTIAL))}",
            "",
            f"Maximum propagation depth: {self.max_depth}",
            f"Total impact score: {self.total_impact_score:.2f}",
        ]

        if self.recommendations:
            parts.append("")
            parts.append("Recommendations:")
            for i, rec in enumerate(self.recommendations, 1):
                parts.append(f"  {i}. {rec}")

        return "\n".join(parts)


class ChangeRequest(BaseModel):
    """
    Request to analyze the impact of a proposed change.

    Used when a developer wants to understand what parts
    of the codebase might be affected by their changes.

    Attributes:
        entity_id: ID of entity being changed (if known)
        entity_name: Name of entity being changed
        file_path: File being modified
        change_description: Description of the change
        change_type: Type of change being made
        max_depth: Maximum depth for impact traversal
    """

    entity_id: UUID | None = Field(
        default=None,
        description="ID of entity being changed"
    )
    entity_name: str | None = Field(
        default=None,
        description="Name of entity being changed"
    )
    file_path: str = Field(
        description="File being modified"
    )
    change_description: str = Field(
        default="",
        description="Description of the change"
    )
    change_type: str = Field(
        default="modification",
        description="Type: modification, deletion, signature_change"
    )
    max_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum traversal depth"
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate that either entity_id or entity_name is provided."""
        if not self.entity_id and not self.entity_name:
            raise ValueError(
                "Either 'entity_id' or 'entity_name' must be provided"
            )
