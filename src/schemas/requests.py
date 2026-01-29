"""
Request Schemas
===============

Defines Pydantic models for API request validation.
These schemas ensure incoming data is properly formatted.

HOW IT WORKS:
    1. FastAPI uses these schemas to validate incoming JSON
    2. Invalid requests are automatically rejected with 422 error
    3. Valid requests are converted to Pydantic models
    4. Services receive typed, validated data

USAGE IN API:
    @router.post("/analyze")
    async def analyze_repo(request: AnalyzeRepositoryRequest):
        # request is already validated!
        repo_url = request.url
"""

from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class AnalyzeRepositoryRequest(BaseModel):
    """
    Request to analyze a code repository.

    Send this to start analyzing a repository.
    Either `url` OR `local_path` must be provided.

    Example JSON:
        {
            "url": "https://github.com/user/project",
            "branch": "main",
            "language": "python"
        }
    """

    url: str | None = Field(
        default=None,
        description="GitHub/GitLab repository URL",
        examples=["https://github.com/fastapi/fastapi"]
    )
    local_path: str | None = Field(
        default=None,
        description="Path to local repository",
        examples=["/home/user/projects/myproject"]
    )
    branch: str = Field(
        default="main",
        description="Branch to analyze",
        examples=["main", "develop", "feature/new-feature"]
    )
    language: str | None = Field(
        default=None,
        description="Programming language (auto-detected if not provided)",
        examples=["python", "javascript", "typescript"]
    )
    force_reanalyze: bool = Field(
        default=False,
        description="Force re-analysis even if already indexed"
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate that either url or local_path is provided."""
        if not self.url and not self.local_path:
            raise ValueError("Either 'url' or 'local_path' must be provided")


class ImpactAnalysisRequest(BaseModel):
    """
    Request for impact analysis.

    Send this to find out what parts of the codebase
    would be affected by changing a specific entity.

    Example JSON:
        {
            "repository_id": "550e8400-e29b-41d4-a716-446655440000",
            "entity_name": "process_data",
            "file_path": "src/services/processor.py",
            "change_description": "Changing return type from dict to list"
        }
    """

    repository_id: str = Field(
        description="UUID of the analyzed repository",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    entity_id: str | None = Field(
        default=None,
        description="UUID of the entity to analyze (if known)",
        examples=["550e8400-e29b-41d4-a716-446655440001"]
    )
    entity_name: str | None = Field(
        default=None,
        description="Name of the entity to analyze",
        examples=["process_data", "UserService", "validate_input"]
    )
    file_path: str | None = Field(
        default=None,
        description="File path to help identify the entity",
        examples=["src/services/processor.py"]
    )
    change_description: str = Field(
        default="",
        description="Description of the proposed change",
        examples=["Changing return type from dict to list"]
    )
    change_type: str = Field(
        default="modification",
        description="Type of change: modification, deletion, signature_change",
        examples=["modification", "deletion", "signature_change"]
    )
    max_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum depth for impact traversal (1-10)"
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate that either entity_id or entity_name is provided."""
        if not self.entity_id and not self.entity_name:
            raise ValueError(
                "Either 'entity_id' or 'entity_name' must be provided"
            )


class CodeGenerationRequest(BaseModel):
    """
    Request for AI code generation.

    Send this to generate code based on existing codebase
    patterns, similar code, and LLM capabilities.

    Example JSON:
        {
            "repository_id": "550e8400-e29b-41d4-a716-446655440000",
            "prompt": "Create a function to validate email addresses",
            "context_entities": ["validate_phone", "validate_username"],
            "target_file": "src/validators/email.py"
        }
    """

    repository_id: str = Field(
        description="UUID of the analyzed repository",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    prompt: str = Field(
        description="Description of code to generate",
        min_length=10,
        examples=[
            "Create a function to validate email addresses",
            "Add a method to calculate user statistics",
            "Implement error handling for the API endpoint"
        ]
    )
    context_entities: list[str] = Field(
        default_factory=list,
        description="Names of related entities to use as context",
        examples=[["validate_phone", "validate_username"]]
    )
    target_file: str | None = Field(
        default=None,
        description="Target file path for the generated code",
        examples=["src/validators/email.py"]
    )
    similar_code_count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of similar code examples to retrieve"
    )
    include_tests: bool = Field(
        default=False,
        description="Whether to generate tests for the code"
    )
    style_guide: str | None = Field(
        default=None,
        description="Specific style guidelines to follow",
        examples=["Follow PEP 8, use type hints, add docstrings"]
    )


class SemanticSearchRequest(BaseModel):
    """
    Request for semantic code search.

    Send this to find code similar to a natural language query.
    Uses vector embeddings for semantic matching.

    Example JSON:
        {
            "repository_id": "550e8400-e29b-41d4-a716-446655440000",
            "query": "function that validates user input",
            "limit": 10
        }
    """

    repository_id: str = Field(
        description="UUID of the analyzed repository",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    query: str = Field(
        description="Natural language search query",
        min_length=3,
        examples=[
            "function that validates user input",
            "class for handling database connections",
            "error handling for API requests"
        ]
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )
    entity_types: list[str] | None = Field(
        default=None,
        description="Filter by entity types (function, class, module)",
        examples=[["function", "class"]]
    )
    file_pattern: str | None = Field(
        default=None,
        description="Glob pattern to filter files",
        examples=["src/**/*.py", "tests/*.py"]
    )
    min_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score (0-1)"
    )


class GraphQueryRequest(BaseModel):
    """
    Request for direct knowledge graph queries.

    Send this to query the Neo4j knowledge graph directly.
    Supports finding relationships and paths between entities.

    Example JSON:
        {
            "repository_id": "550e8400-e29b-41d4-a716-446655440000",
            "query_type": "callers",
            "entity_name": "process_data"
        }
    """

    repository_id: str = Field(
        description="UUID of the analyzed repository"
    )
    query_type: str = Field(
        description="Type of query: callers, callees, dependencies, dependents",
        examples=["callers", "callees", "dependencies", "dependents"]
    )
    entity_name: str = Field(
        description="Name of the entity to query"
    )
    entity_id: str | None = Field(
        default=None,
        description="UUID of the entity (if known)"
    )
    max_depth: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum traversal depth"
    )
