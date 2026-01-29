"""
Impact Analysis Service
=======================

Analyzes the potential impact of code changes across the codebase.
This is a key feature for understanding change consequences.

WHAT IS IMPACT ANALYSIS?
    Impact analysis answers: "If I change this code, what else
    might break or need to be updated?"

    It traverses the knowledge graph to find all code entities
    that depend on the changed entity, directly or indirectly.

HOW IT WORKS:
    1. Identify the entity being changed
    2. Query Neo4j for all dependent entities
    3. Calculate impact scores based on:
       - Distance from the changed entity
       - Type of relationship (call vs inheritance)
       - Criticality of the dependent code
    4. Rank and categorize impacts
    5. Generate recommendations

IMPACT SCORING:
    Impact Score = Base Score × Distance Decay × Relationship Weight

    Distance Decay: 1.0 for direct, 0.7 for 2 hops, 0.5 for 3 hops
    Relationship Weights:
        - CALLS: 0.9 (high impact)
        - INHERITS: 1.0 (highest impact)
        - USES: 0.7
        - IMPORTS: 0.5

DATA FLOW:
    Change Request (entity_id or name)
           ↓
    Identify Entity in Neo4j
           ↓
    Traverse Graph (find dependents)
           ↓
    Calculate Impact Scores
           ↓
    Categorize by Impact Level
           ↓
    Generate Recommendations
           ↓
    ImpactAnalysis Result

VISUAL EXAMPLE:
    Changing: validate_email()
           ↓
    DIRECT IMPACT (1 hop):
      - register_user() - CALLS validate_email
      - update_profile() - CALLS validate_email
           ↓
    INDIRECT IMPACT (2 hops):
      - signup_endpoint() - CALLS register_user
      - profile_api() - CALLS update_profile
           ↓
    POTENTIAL IMPACT (3 hops):
      - main_app() - IMPORTS signup_endpoint

USAGE:
    from src.services.impact_analyzer import ImpactAnalyzer

    analyzer = ImpactAnalyzer(neo4j, vector_svc)

    # Analyze impact
    impact = await analyzer.analyze(
        repository_id="repo-123",
        entity_name="validate_email",
        max_depth=3
    )

    print(impact.summary)
    for entity in impact.impacted_entities:
        print(f"  {entity.name}: {entity.impact_level}")
"""

from typing import Any
from uuid import UUID, uuid4

from src.core.logging import LoggerMixin
from src.models.code_entity import CodeEntityType
from src.models.impact import (
    ChangeRequest,
    ImpactAnalysis,
    ImpactCategory,
    ImpactedEntity,
    ImpactLevel,
)
from src.services.neo4j_service import Neo4jService
from src.services.vector_service import VectorService


# Relationship type to impact weight mapping
RELATIONSHIP_WEIGHTS: dict[str, float] = {
    "INHERITS": 1.0,       # Inheritance changes have highest impact
    "CALLS": 0.9,          # Call changes usually require updates
    "USES": 0.7,           # Usage might need changes
    "IMPORTS": 0.5,        # Import changes might need updates
    "CONTAINS": 0.3,       # Container changes have lower direct impact
    "DECORATES": 0.6,      # Decorator changes can affect behavior
    "RETURNS": 0.8,        # Return type changes affect callers
    "ACCEPTS": 0.8,        # Parameter type changes affect callers
}

# Distance decay factors
DISTANCE_DECAY: dict[int, float] = {
    1: 1.0,    # Direct dependency
    2: 0.7,    # One hop away
    3: 0.5,    # Two hops away
    4: 0.3,    # Three hops away
    5: 0.2,    # Far away
}


class ImpactAnalyzer(LoggerMixin):
    """
    Service for analyzing code change impact.

    Uses the knowledge graph to trace dependencies and
    calculate impact scores.

    Attributes:
        neo4j: Neo4j service for graph queries
        vector: Vector service for semantic analysis
    """

    def __init__(
        self,
        neo4j: Neo4jService,
        vector: VectorService
    ) -> None:
        """
        Initialize the impact analyzer.

        Args:
            neo4j: Neo4j service instance
            vector: Vector service instance
        """
        self.neo4j = neo4j
        self.vector = vector

    async def analyze(
        self,
        repository_id: str,
        entity_id: str | None = None,
        entity_name: str | None = None,
        file_path: str | None = None,
        change_description: str = "",
        change_type: str = "modification",
        max_depth: int = 3
    ) -> ImpactAnalysis:
        """
        Analyze the impact of changing a code entity.

        Args:
            repository_id: UUID of the repository
            entity_id: UUID of the entity (if known)
            entity_name: Name of the entity (if ID unknown)
            file_path: File path to help identify entity
            change_description: Description of the planned change
            change_type: Type: modification, deletion, signature_change
            max_depth: Maximum depth for impact traversal

        Returns:
            ImpactAnalysis with all impacted entities

        Example:
            impact = await analyzer.analyze(
                repository_id="repo-123",
                entity_name="process_data",
                change_description="Changing return type from dict to list",
                change_type="signature_change"
            )
        """
        self.logger.info(
            "Starting impact analysis",
            repository_id=repository_id,
            entity_id=entity_id,
            entity_name=entity_name,
            max_depth=max_depth
        )

        # Find the source entity
        if entity_id:
            source_entity = await self.neo4j.get_entity_by_id(entity_id)
        else:
            source_entity = await self.neo4j.get_entity_by_name(
                entity_name,
                repository_id,
                file_path
            )

        if not source_entity:
            self.logger.warning("Source entity not found")
            return ImpactAnalysis(
                source_entity_id=uuid4(),
                source_entity_name=entity_name or "unknown",
                source_file_path=file_path or "unknown",
                summary="Source entity not found in the knowledge graph."
            )

        # Get all dependent entities from Neo4j
        dependents = await self.neo4j.get_dependents(
            source_entity["id"],
            max_depth=max_depth
        )

        self.logger.info(f"Found {len(dependents)} dependent entities")

        # Calculate impact for each dependent
        impacted_entities = []
        for dep in dependents:
            impacted = await self._calculate_impact(
                dep,
                change_type,
                change_description
            )
            impacted_entities.append(impacted)

        # Sort by impact score
        impacted_entities.sort(key=lambda x: x.impact_score, reverse=True)

        # Calculate totals
        total_impact_score = sum(e.impact_score for e in impacted_entities)
        max_distance = max((e.distance for e in impacted_entities), default=0)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            impacted_entities,
            change_type
        )

        # Build analysis result
        analysis = ImpactAnalysis(
            source_entity_id=UUID(source_entity["id"]),
            source_entity_name=source_entity["name"],
            source_file_path=source_entity["file_path"],
            impacted_entities=impacted_entities,
            total_impact_score=total_impact_score,
            max_depth=max_distance,
            recommendations=recommendations
        )

        # Generate summary
        analysis.summary = analysis.generate_summary()

        self.logger.info(
            "Impact analysis complete",
            total_impacted=len(impacted_entities),
            total_score=total_impact_score
        )

        return analysis

    async def _calculate_impact(
        self,
        dependent: dict[str, Any],
        change_type: str,
        change_description: str
    ) -> ImpactedEntity:
        """
        Calculate impact score for a single dependent entity.

        Args:
            dependent: Dependent entity data from Neo4j
            change_type: Type of change being made
            change_description: Description of the change

        Returns:
            ImpactedEntity with calculated scores
        """
        entity = dependent["entity"]
        distance = dependent["distance"]
        relationship_path = dependent.get("relationship_path", [])

        # Base score starts at 10
        base_score = 10.0

        # Apply distance decay
        decay = DISTANCE_DECAY.get(distance, 0.1)
        score = base_score * decay

        # Apply relationship weight (use highest weight in path)
        if relationship_path:
            max_weight = max(
                RELATIONSHIP_WEIGHTS.get(rel, 0.5)
                for rel in relationship_path
            )
            score *= max_weight

        # Adjust for change type
        if change_type == "deletion":
            score *= 1.5  # Deletions have higher impact
        elif change_type == "signature_change":
            score *= 1.3  # Signature changes affect callers

        # Determine impact level
        impact_level = self._determine_impact_level(score, distance)

        # Determine categories
        categories = self._determine_categories(
            entity,
            relationship_path,
            change_type
        )

        # Generate reason
        reason = self._generate_reason(
            entity,
            relationship_path,
            distance
        )

        # Generate suggested action
        suggested_action = self._generate_action(
            impact_level,
            categories,
            change_type
        )

        return ImpactedEntity(
            entity_id=UUID(entity["id"]),
            entity_name=entity["name"],
            entity_type=CodeEntityType(entity.get("entity_type", "function")),
            file_path=entity["file_path"],
            impact_level=impact_level,
            impact_score=round(score, 2),
            distance=distance,
            relationship_path=relationship_path,
            reason=reason,
            categories=categories,
            suggested_action=suggested_action
        )

    def _determine_impact_level(
        self,
        score: float,
        distance: int
    ) -> ImpactLevel:
        """
        Determine the impact level based on score and distance.

        Args:
            score: Calculated impact score
            distance: Relationship distance

        Returns:
            ImpactLevel enum value
        """
        if score >= 8.0 and distance == 1:
            return ImpactLevel.CRITICAL
        elif distance == 1 or score >= 6.0:
            return ImpactLevel.DIRECT
        elif distance <= 2 or score >= 4.0:
            return ImpactLevel.INDIRECT
        elif score >= 2.0:
            return ImpactLevel.POTENTIAL
        else:
            return ImpactLevel.MINIMAL

    def _determine_categories(
        self,
        entity: dict[str, Any],
        relationship_path: list[str],
        change_type: str
    ) -> list[ImpactCategory]:
        """
        Determine impact categories for an entity.

        Args:
            entity: Entity data
            relationship_path: Path of relationships
            change_type: Type of change

        Returns:
            List of applicable impact categories
        """
        categories = []

        # Check relationship types
        if "CALLS" in relationship_path:
            categories.append(ImpactCategory.FUNCTIONALITY)
        if "INHERITS" in relationship_path:
            categories.append(ImpactCategory.API)
        if "RETURNS" in relationship_path or "ACCEPTS" in relationship_path:
            categories.append(ImpactCategory.DATA)

        # Check entity name patterns
        entity_name = entity.get("name", "").lower()
        if "test" in entity_name or "_test" in entity_name:
            categories.append(ImpactCategory.TESTING)
        if "api" in entity_name or "endpoint" in entity_name:
            categories.append(ImpactCategory.API)
        if "auth" in entity_name or "security" in entity_name:
            categories.append(ImpactCategory.SECURITY)

        return list(set(categories)) or [ImpactCategory.FUNCTIONALITY]

    def _generate_reason(
        self,
        entity: dict[str, Any],
        relationship_path: list[str],
        distance: int
    ) -> str:
        """
        Generate a human-readable reason for the impact.

        Args:
            entity: Entity data
            relationship_path: Path of relationships
            distance: Relationship distance

        Returns:
            Reason string
        """
        entity_name = entity["name"]
        path_str = " → ".join(relationship_path) if relationship_path else "unknown"

        if distance == 1:
            if "CALLS" in relationship_path:
                return f"'{entity_name}' directly calls the changed function"
            elif "INHERITS" in relationship_path:
                return f"'{entity_name}' inherits from the changed class"
            elif "USES" in relationship_path:
                return f"'{entity_name}' directly uses the changed entity"
            else:
                return f"'{entity_name}' has a direct relationship ({path_str})"
        else:
            return f"'{entity_name}' is {distance} hops away via {path_str}"

    def _generate_action(
        self,
        impact_level: ImpactLevel,
        categories: list[ImpactCategory],
        change_type: str
    ) -> str:
        """
        Generate a suggested action for the impacted entity.

        Args:
            impact_level: Level of impact
            categories: Impact categories
            change_type: Type of change

        Returns:
            Suggested action string
        """
        if impact_level == ImpactLevel.CRITICAL:
            if change_type == "deletion":
                return "URGENT: Update or remove calls to deleted function"
            elif change_type == "signature_change":
                return "URGENT: Update function call signature"
            else:
                return "URGENT: Review and update for compatibility"

        elif impact_level == ImpactLevel.DIRECT:
            if ImpactCategory.TESTING in categories:
                return "Update related tests"
            elif ImpactCategory.API in categories:
                return "Review API compatibility"
            else:
                return "Review for compatibility with changes"

        elif impact_level == ImpactLevel.INDIRECT:
            return "Consider reviewing for potential issues"

        else:
            return "Low priority - verify no issues"

    def _generate_recommendations(
        self,
        impacted_entities: list[ImpactedEntity],
        change_type: str
    ) -> list[str]:
        """
        Generate overall recommendations based on impact analysis.

        Args:
            impacted_entities: All impacted entities
            change_type: Type of change

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Count by level
        critical_count = sum(
            1 for e in impacted_entities
            if e.impact_level == ImpactLevel.CRITICAL
        )
        direct_count = sum(
            1 for e in impacted_entities
            if e.impact_level == ImpactLevel.DIRECT
        )

        if critical_count > 0:
            recommendations.append(
                f"🚨 {critical_count} critical impacts require immediate attention"
            )

        if direct_count > 5:
            recommendations.append(
                "Consider breaking the change into smaller, incremental updates"
            )

        # Check for test impacts
        test_impacts = [
            e for e in impacted_entities
            if ImpactCategory.TESTING in e.categories
        ]
        if test_impacts:
            recommendations.append(
                f"Update {len(test_impacts)} affected tests before merging"
            )

        # Check for API impacts
        api_impacts = [
            e for e in impacted_entities
            if ImpactCategory.API in e.categories
        ]
        if api_impacts:
            recommendations.append(
                "API changes detected - consider versioning or deprecation notice"
            )

        # General recommendations
        if len(impacted_entities) > 20:
            recommendations.append(
                "Large impact radius - consider extensive testing"
            )

        if change_type == "deletion":
            recommendations.append(
                "Ensure all references are removed before deletion"
            )

        if not recommendations:
            recommendations.append(
                "Low overall impact - proceed with normal review process"
            )

        return recommendations

    async def get_change_summary(
        self,
        impact: ImpactAnalysis
    ) -> dict[str, Any]:
        """
        Get a structured summary of the impact analysis.

        Args:
            impact: Completed impact analysis

        Returns:
            Summary dict suitable for API response
        """
        # Group by file
        by_file: dict[str, list[ImpactedEntity]] = {}
        for entity in impact.impacted_entities:
            file_path = entity.file_path
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(entity)

        return {
            "source": {
                "name": impact.source_entity_name,
                "file": impact.source_file_path
            },
            "statistics": {
                "total_impacted": impact.total_count,
                "critical": impact.critical_count,
                "direct": impact.direct_count,
                "indirect": impact.indirect_count,
                "total_score": impact.total_impact_score,
                "max_depth": impact.max_depth
            },
            "by_file": {
                file: [e.entity_name for e in entities]
                for file, entities in by_file.items()
            },
            "recommendations": impact.recommendations
        }
