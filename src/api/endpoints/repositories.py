"""
Repository Endpoints
====================

Endpoints for repository analysis and management.

ENDPOINTS:
    POST /repositories         - Analyze a new repository
    GET /repositories          - List all repositories
    GET /repositories/{id}     - Get repository details
    DELETE /repositories/{id}  - Delete a repository

DATA FLOW:
    POST /repositories
          ↓
    RepositoryService.analyze()
          ↓
    Clone (if remote) → Parse → Index
          ↓
    Return Repository status

USAGE:
    # Analyze a GitHub repository
    curl -X POST http://localhost:8000/api/v1/repositories \\
         -H "Content-Type: application/json" \\
         -d '{"url": "https://github.com/user/repo"}'

    # Analyze a local repository
    curl -X POST http://localhost:8000/api/v1/repositories \\
         -H "Content-Type: application/json" \\
         -d '{"local_path": "/path/to/repo"}'
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Any

from src.api.dependencies import get_repository_service
from src.schemas.requests import AnalyzeRepositoryRequest
from src.schemas.responses import RepositoryResponse, ErrorResponse
from src.services.repository_service import RepositoryService

router = APIRouter()


@router.post(
    "",
    response_model=RepositoryResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Analysis failed"}
    },
    summary="Analyze Repository",
    description="Start analysis of a code repository. Can be GitHub URL or local path."
)
async def analyze_repository(
    request: AnalyzeRepositoryRequest,
    background_tasks: BackgroundTasks,
    repo_service: RepositoryService = Depends(get_repository_service)
) -> RepositoryResponse:
    """
    Analyze a code repository.

    This endpoint:
    1. Clones the repository (if remote URL)
    2. Parses the code using CodeQL/AST
    3. Indexes entities in Neo4j (knowledge graph)
    4. Creates embeddings in ChromaDB (vector search)

    Args:
        request: Repository analysis request
        background_tasks: FastAPI background tasks
        repo_service: Repository service dependency

    Returns:
        Repository status and metadata

    Example Request:
        {
            "url": "https://github.com/fastapi/fastapi",
            "branch": "main",
            "language": "python"
        }

    Example Response:
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "fastapi",
            "status": "analyzing",
            "entity_count": 0,
            "created_at": "2024-01-29T10:30:00Z"
        }
    """
    try:
        # Start analysis (this may take a while for large repos)
        repo = await repo_service.analyze(
            url=request.url,
            local_path=request.local_path,
            branch=request.branch,
            language=request.language,
            force_reanalyze=request.force_reanalyze
        )

        return RepositoryResponse(
            id=str(repo.id),
            name=repo.name,
            url=repo.url,
            local_path=repo.local_path,
            status=repo.status,
            entity_count=repo.entity_count,
            relationship_count=repo.relationship_count,
            language=repo.language,
            branch=repo.branch,
            error_message=repo.error_message,
            created_at=repo.created_at,
            completed_at=repo.completed_at
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "",
    response_model=list[dict[str, Any]],
    summary="List Repositories",
    description="Get a list of all analyzed repositories"
)
async def list_repositories(
    repo_service: RepositoryService = Depends(get_repository_service)
) -> list[dict[str, Any]]:
    """
    List all tracked repositories.

    Returns:
        List of repository summaries
    """
    return await repo_service.list_repositories()


@router.get(
    "/{repository_id}",
    response_model=dict[str, Any],
    responses={
        404: {"model": ErrorResponse, "description": "Repository not found"}
    },
    summary="Get Repository",
    description="Get details and status of a specific repository"
)
async def get_repository(
    repository_id: str,
    repo_service: RepositoryService = Depends(get_repository_service)
) -> dict[str, Any]:
    """
    Get repository details by ID.

    Args:
        repository_id: UUID of the repository

    Returns:
        Repository details and status
    """
    status = await repo_service.get_status(repository_id)

    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Repository not found")

    return status


@router.delete(
    "/{repository_id}",
    responses={
        404: {"model": ErrorResponse, "description": "Repository not found"}
    },
    summary="Delete Repository",
    description="Delete a repository and all its indexed data"
)
async def delete_repository(
    repository_id: str,
    repo_service: RepositoryService = Depends(get_repository_service)
) -> dict[str, str]:
    """
    Delete a repository and all its indexed data.

    This removes:
    - All entities from Neo4j
    - All embeddings from ChromaDB
    - Local clone (if was cloned)

    Args:
        repository_id: UUID of the repository

    Returns:
        Deletion confirmation
    """
    deleted = await repo_service.delete_repository(repository_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Repository not found")

    return {"message": "Repository deleted successfully", "id": repository_id}
