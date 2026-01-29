"""
Models Module
=============

Defines the data models used throughout the application.
These represent the core entities in our code analysis system.

Models:
    - CodeEntity: Represents a code element (function, class, etc.)
    - Relationship: Represents a connection between code entities
    - Repository: Represents an analyzed repository
    - ImpactAnalysis: Represents impact analysis results
"""

from src.models.code_entity import (
    CodeEntity,
    CodeEntityType,
    FunctionEntity,
    ClassEntity,
    ModuleEntity,
    VariableEntity,
)
from src.models.relationship import (
    Relationship,
    RelationshipType,
)
from src.models.repository import Repository, RepositoryStatus
from src.models.impact import ImpactAnalysis, ImpactedEntity

__all__ = [
    "CodeEntity",
    "CodeEntityType",
    "FunctionEntity",
    "ClassEntity",
    "ModuleEntity",
    "VariableEntity",
    "Relationship",
    "RelationshipType",
    "Repository",
    "RepositoryStatus",
    "ImpactAnalysis",
    "ImpactedEntity",
]
