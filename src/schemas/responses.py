"""
Response Schemas
================

Defines Pydantic models for API responses.
These schemas ensure consistent response formats.

HOW IT WORKS:
    1. Services return data in these formats
    2. FastAPI serializes them to JSON
    3. OpenAPI docs show the response structure
    4. Clients know exactly what to expect

USAGE IN API:
    @router.get("/repository/{id}", response_model=RepositoryResponse)
    async def get_repo(id: str):
        return RepositoryResponse(...)
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Health check response.

    Returned by /health endpoint to indicate service status.

    Example Response:
        {
            "status": "healthy",
            "version": "1.0.0",
            "services": {
                "neo4j": "connected",
                "chromadb": "connected",
                "openai": "connected"
            }
        }
    """

    status: str = Field(
        description="Overall health status",
        examples=["healthy", "degraded", "unhealthy"]
    )
    version: str = Field(
        description="API version",
        examples=["1.0.0"]
    )
    services: dict[str, str] = Field(
        description="Status of individual services",
        examples=[{
            "neo4j": "connected",
            "chromadb": "connected",
            "openai": "connected"
        }]
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )


class ErrorResponse(BaseModel):
    """
    Error response format.

    Returned when an error occurs during request processing.

    Example Response:
        {
            "error": "REPOSITORY_NOT_FOUND",
            "message": "Repository not found: invalid-url",
            "details": {"repository_url": "invalid-url"}
        }
    """

    error: str = Field(
        description="Error code",
        examples=["REPOSITORY_NOT_FOUND", "VALIDATION_ERROR"]
    )
    message: str = Field(
        description="Human-readable error message"
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional error details"
    )


class RepositoryResponse(BaseModel):
    """
    Repository information response.

    Returned after analyzing a repository or querying its status.

    Example Response:
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "fastapi",
            "url": "https://github.com/fastapi/fastapi",
            "status": "ready",
            "entity_count": 1250,
            "relationship_count": 3800,
            "language": "python"
        }
    """

    id: str = Field(
        description="Repository UUID"
    )
    name: str = Field(
        description="Repository name"
    )
    url: str | None = Field(
        default=None,
        description="Repository URL (if remote)"
    )
    local_path: str | None = Field(
        default=None,
        description="Local path (if local)"
    )
    status: str = Field(
        description="Processing status",
        examples=["pending", "analyzing", "ready", "failed"]
    )
    entity_count: int = Field(
        default=0,
        description="Number of code entities found"
    )
    relationship_count: int = Field(
        default=0,
        description="Number of relationships found"
    )
    language: str = Field(
        description="Primary programming language"
    )
    branch: str = Field(
        default="main",
        description="Analyzed branch"
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if status is 'failed'"
    )
    created_at: datetime = Field(
        description="When analysis started"
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When analysis completed"
    )


class EntityResponse(BaseModel):
    """
    Code entity information response.

    Represents a single code entity (function, class, etc.).

    Example Response:
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "name": "process_data",
            "entity_type": "function",
            "file_path": "src/processor.py",
            "start_line": 42,
            "end_line": 85,
            "signature": "def process_data(items: list) -> dict"
        }
    """

    id: str = Field(
        description="Entity UUID"
    )
    name: str = Field(
        description="Entity name"
    )
    qualified_name: str = Field(
        default="",
        description="Full qualified name"
    )
    entity_type: str = Field(
        description="Type: function, class, module, variable"
    )
    file_path: str = Field(
        description="Source file path"
    )
    start_line: int = Field(
        description="Starting line number"
    )
    end_line: int = Field(
        description="Ending line number"
    )
    signature: str | None = Field(
        default=None,
        description="Function/method signature"
    )
    docstring: str | None = Field(
        default=None,
        description="Documentation string"
    )
    source_code: str | None = Field(
        default=None,
        description="Source code (if requested)"
    )


class ImpactedEntityResponse(BaseModel):
    """
    Impacted entity in impact analysis response.

    Example Response:
        {
            "entity_id": "550e8400-e29b-41d4-a716-446655440002",
            "entity_name": "handle_request",
            "entity_type": "function",
            "file_path": "src/api/handlers.py",
            "impact_level": "direct",
            "impact_score": 8.5,
            "distance": 1,
            "reason": "Directly calls the changed function"
        }
    """

    entity_id: str = Field(
        description="UUID of impacted entity"
    )
    entity_name: str = Field(
        description="Name of the entity"
    )
    entity_type: str = Field(
        description="Type of entity"
    )
    file_path: str = Field(
        description="File containing the entity"
    )
    impact_level: str = Field(
        description="Impact severity: critical, direct, indirect, potential"
    )
    impact_score: float = Field(
        description="Numeric impact score (0-10)"
    )
    distance: int = Field(
        description="Hops from source entity"
    )
    relationship_path: list[str] = Field(
        default_factory=list,
        description="Relationship types in path"
    )
    reason: str = Field(
        description="Why this entity is impacted"
    )
    suggested_action: str = Field(
        default="Review for compatibility",
        description="Recommended action"
    )


class ImpactAnalysisResponse(BaseModel):
    """
    Complete impact analysis response.

    Returned after analyzing the impact of a code change.

    Example Response:
        {
            "id": "550e8400-e29b-41d4-a716-446655440003",
            "source_entity": {...},
            "impacted_entities": [...],
            "summary": {
                "total_count": 15,
                "critical_count": 2,
                "direct_count": 5,
                "indirect_count": 8
            }
        }
    """

    id: str = Field(
        description="Analysis UUID"
    )
    source_entity: EntityResponse = Field(
        description="The entity being changed"
    )
    impacted_entities: list[ImpactedEntityResponse] = Field(
        default_factory=list,
        description="All impacted entities"
    )
    summary: dict[str, Any] = Field(
        description="Impact summary statistics"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommended actions"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When analysis was performed"
    )


class SearchResultResponse(BaseModel):
    """
    Single search result response.

    Example Response:
        {
            "entity": {...},
            "score": 0.92,
            "snippet": "def validate_email(email: str) -> bool: ..."
        }
    """

    entity: EntityResponse = Field(
        description="Matching entity"
    )
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Similarity score (0-1)"
    )
    snippet: str | None = Field(
        default=None,
        description="Code snippet preview"
    )


class SemanticSearchResponse(BaseModel):
    """
    Semantic search results response.

    Returned after searching code with natural language.

    Example Response:
        {
            "query": "function that validates user input",
            "results": [...],
            "total_count": 10
        }
    """

    query: str = Field(
        description="Original search query"
    )
    results: list[SearchResultResponse] = Field(
        default_factory=list,
        description="Search results"
    )
    total_count: int = Field(
        description="Total number of results"
    )


class GeneratedCodeResponse(BaseModel):
    """
    Generated code response.

    Returned after AI code generation.

    Example Response:
        {
            "code": "def validate_email(email: str) -> bool:\\n    ...",
            "explanation": "This function validates email addresses...",
            "similar_examples": [...],
            "tests": "def test_validate_email(): ..."
        }
    """

    code: str = Field(
        description="Generated source code"
    )
    explanation: str = Field(
        description="Explanation of the generated code"
    )
    similar_examples: list[EntityResponse] = Field(
        default_factory=list,
        description="Similar code used as context"
    )
    tests: str | None = Field(
        default=None,
        description="Generated tests (if requested)"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Model's confidence in the generation"
    )
    tokens_used: int = Field(
        default=0,
        description="Number of tokens used"
    )


class CodeGenerationResponse(BaseModel):
    """
    Complete code generation response.

    Example Response:
        {
            "id": "550e8400-e29b-41d4-a716-446655440004",
            "prompt": "Create a function to validate emails",
            "generated": {...},
            "metadata": {...}
        }
    """

    id: str = Field(
        description="Generation UUID"
    )
    prompt: str = Field(
        description="Original prompt"
    )
    generated: GeneratedCodeResponse = Field(
        description="Generated code and metadata"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When code was generated"
    )
