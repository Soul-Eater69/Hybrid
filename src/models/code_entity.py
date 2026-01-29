"""
Code Entity Models
==================

Defines models for code entities (functions, classes, modules, etc.).
These represent the "nodes" in our knowledge graph.

HOW IT WORKS:
    1. CodeQL parses source code and extracts entities
    2. Each entity becomes a CodeEntity object
    3. Entities are stored in Neo4j (as nodes) and Vector DB (as embeddings)
    4. Relationships between entities are tracked separately

ENTITY TYPES:
    - MODULE: A Python file/module
    - CLASS: A class definition
    - FUNCTION: A function or method
    - VARIABLE: A variable or constant

DATA FLOW:
    Source Code (file.py)
          ↓
    CodeQL Parser
          ↓
    CodeEntity Objects
          ↓
    ┌─────┴─────┐
    ↓           ↓
    Neo4j    Vector DB
    (graph)  (embeddings)

USAGE:
    from src.models.code_entity import FunctionEntity

    # Create a function entity
    func = FunctionEntity(
        name="calculate_total",
        file_path="src/utils/math.py",
        start_line=10,
        end_line=25,
        signature="def calculate_total(items: list[Item]) -> float",
        docstring="Calculate total price of items.",
        source_code="def calculate_total(items):\\n    return sum(i.price for i in items)"
    )
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CodeEntityType(str, Enum):
    """
    Types of code entities we can identify and track.

    These map to different node types in the Neo4j knowledge graph.
    """

    MODULE = "module"        # A Python file/module
    CLASS = "class"          # A class definition
    FUNCTION = "function"    # A function or method
    VARIABLE = "variable"    # A variable or constant
    IMPORT = "import"        # An import statement
    DECORATOR = "decorator"  # A decorator


class CodeEntity(BaseModel):
    """
    Base model for all code entities.

    This is the parent class for all specific entity types.
    Contains common attributes shared by all code elements.

    Attributes:
        id: Unique identifier for this entity
        entity_type: Type of entity (function, class, etc.)
        name: Name of the entity (function name, class name, etc.)
        qualified_name: Full qualified name including module path
        file_path: Path to the file containing this entity
        start_line: Starting line number in the file
        end_line: Ending line number in the file
        source_code: The actual source code of this entity
        docstring: Documentation string if present
        metadata: Additional metadata from CodeQL analysis
        embedding_id: Reference to vector embedding in ChromaDB
        created_at: When this entity was first analyzed
        updated_at: When this entity was last updated
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this entity"
    )
    entity_type: CodeEntityType = Field(
        description="Type of code entity"
    )
    name: str = Field(
        description="Name of the entity"
    )
    qualified_name: str = Field(
        default="",
        description="Full qualified name (e.g., 'module.class.method')"
    )
    file_path: str = Field(
        description="Path to the source file"
    )
    start_line: int = Field(
        ge=1,
        description="Starting line number (1-indexed)"
    )
    end_line: int = Field(
        ge=1,
        description="Ending line number (1-indexed)"
    )
    source_code: str = Field(
        default="",
        description="The actual source code"
    )
    docstring: str | None = Field(
        default=None,
        description="Documentation string if present"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata from analysis"
    )
    embedding_id: str | None = Field(
        default=None,
        description="Reference to vector embedding in ChromaDB"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this entity was first analyzed"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this entity was last updated"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True

    def to_neo4j_properties(self) -> dict[str, Any]:
        """
        Convert entity to Neo4j node properties.

        Returns a flat dictionary suitable for creating/updating
        a Neo4j node. Complex types are serialized to strings.

        Returns:
            Dictionary of node properties
        """
        return {
            "id": str(self.id),
            "entity_type": self.entity_type,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "source_code": self.source_code,
            "docstring": self.docstring or "",
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_embedding_document(self) -> str:
        """
        Create a document string for vector embedding.

        Combines relevant information into a single string
        that captures the semantic meaning of this entity.

        Returns:
            String to be embedded in vector DB
        """
        parts = [
            f"# {self.entity_type.upper()}: {self.qualified_name or self.name}",
            f"File: {self.file_path}",
        ]
        if self.docstring:
            parts.append(f"Documentation: {self.docstring}")
        parts.append(f"Code:\n{self.source_code}")
        return "\n".join(parts)


class FunctionEntity(CodeEntity):
    """
    Represents a function or method in the codebase.

    Extends CodeEntity with function-specific attributes.

    Additional Attributes:
        signature: The function signature (def line)
        parameters: List of parameter names and types
        return_type: The return type annotation if present
        is_method: True if this is a class method
        is_async: True if this is an async function
        decorators: List of decorators applied to this function
        complexity: Cyclomatic complexity score
    """

    entity_type: CodeEntityType = Field(
        default=CodeEntityType.FUNCTION,
        description="Always 'function' for this model"
    )
    signature: str = Field(
        default="",
        description="Function signature (the def line)"
    )
    parameters: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of parameters with name and type"
    )
    return_type: str | None = Field(
        default=None,
        description="Return type annotation"
    )
    is_method: bool = Field(
        default=False,
        description="True if this is a class method"
    )
    is_async: bool = Field(
        default=False,
        description="True if this is an async function"
    )
    decorators: list[str] = Field(
        default_factory=list,
        description="List of decorator names"
    )
    complexity: int = Field(
        default=1,
        ge=1,
        description="Cyclomatic complexity score"
    )


class ClassEntity(CodeEntity):
    """
    Represents a class definition in the codebase.

    Extends CodeEntity with class-specific attributes.

    Additional Attributes:
        bases: List of base class names (inheritance)
        decorators: List of decorators applied to this class
        methods: List of method names in this class
        attributes: List of class attributes
        is_dataclass: True if this is a dataclass
        is_abstract: True if this is an abstract class
    """

    entity_type: CodeEntityType = Field(
        default=CodeEntityType.CLASS,
        description="Always 'class' for this model"
    )
    bases: list[str] = Field(
        default_factory=list,
        description="Base classes (inheritance)"
    )
    decorators: list[str] = Field(
        default_factory=list,
        description="List of decorator names"
    )
    methods: list[str] = Field(
        default_factory=list,
        description="Method names defined in this class"
    )
    attributes: list[str] = Field(
        default_factory=list,
        description="Class attribute names"
    )
    is_dataclass: bool = Field(
        default=False,
        description="True if this is a dataclass"
    )
    is_abstract: bool = Field(
        default=False,
        description="True if this is an abstract class"
    )


class ModuleEntity(CodeEntity):
    """
    Represents a Python module (file) in the codebase.

    Extends CodeEntity with module-specific attributes.

    Additional Attributes:
        imports: List of import statements
        exports: List of exported names (__all__)
        functions: List of top-level function names
        classes: List of class names defined in this module
        global_variables: List of global variable names
    """

    entity_type: CodeEntityType = Field(
        default=CodeEntityType.MODULE,
        description="Always 'module' for this model"
    )
    imports: list[str] = Field(
        default_factory=list,
        description="Import statements in this module"
    )
    exports: list[str] = Field(
        default_factory=list,
        description="Exported names (__all__)"
    )
    functions: list[str] = Field(
        default_factory=list,
        description="Top-level function names"
    )
    classes: list[str] = Field(
        default_factory=list,
        description="Class names in this module"
    )
    global_variables: list[str] = Field(
        default_factory=list,
        description="Global variable names"
    )


class VariableEntity(CodeEntity):
    """
    Represents a variable or constant in the codebase.

    Extends CodeEntity with variable-specific attributes.

    Additional Attributes:
        type_annotation: The type annotation if present
        value: The initial value (if simple enough to capture)
        is_constant: True if this appears to be a constant
        scope: Where this variable is defined (global, class, local)
    """

    entity_type: CodeEntityType = Field(
        default=CodeEntityType.VARIABLE,
        description="Always 'variable' for this model"
    )
    type_annotation: str | None = Field(
        default=None,
        description="Type annotation if present"
    )
    value: str | None = Field(
        default=None,
        description="Initial value (if simple)"
    )
    is_constant: bool = Field(
        default=False,
        description="True if this appears to be a constant"
    )
    scope: str = Field(
        default="global",
        description="Scope: global, class, or local"
    )
