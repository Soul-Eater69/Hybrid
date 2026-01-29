"""
Search Endpoints
================

Endpoints for searching code in analyzed repositories.

SEARCH TYPES:
    1. Semantic Search - Find code by natural language meaning
    2. Structural Search - Find by code relationships
    3. Similar Code - Find code similar to a given entity

ENDPOINTS:
    POST /search/semantic   - Natural language code search
    POST /search/callers    - Find functions that call X
    POST /search/callees    - Find functions called by X
    POST /search/similar    - Find similar code
    POST /search/combined   - Combined semantic + structural

USAGE:
    # Semantic search
    curl -X POST http://localhost:8000/api/v1/search/semantic \\
         -H "Content-Type: application/json" \\
         -d '{"repository_id": "...", "query": "validate user input"}'
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any

from src.api.dependencies import get_search_service
from src.schemas.requests import SemanticSearchRequest, GraphQueryRequest
from src.schemas.responses import SemanticSearchResponse, ErrorResponse
from src.services.search_service import SearchService

router = APIRouter()


@router.post(
    "/semantic",
    response_model=dict[str, Any],
    summary="Semantic Code Search",
    description="Search for code using natural language queries"
)
async def semantic_search(
    request: SemanticSearchRequest,
    search_service: SearchService = Depends(get_search_service)
) -> dict[str, Any]:
    """
    Semantic code search using vector similarity.

    Finds code that is semantically similar to your query,
    even if it uses different words.

    Args:
        request: Search request with query and filters

    Returns:
        Search results with matching code entities

    Example Request:
        {
            "repository_id": "550e8400-e29b-41d4-a716-446655440000",
            "query": "function that validates email addresses",
            "limit": 10,
            "entity_types": ["function"]
        }
    """
    try:
        results = await search_service.semantic_search(
            query=request.query,
            repository_id=request.repository_id,
            limit=request.limit,
            entity_types=request.entity_types,
            file_pattern=request.file_pattern,
            min_score=request.min_score
        )
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/callers",
    response_model=dict[str, Any],
    summary="Find Callers",
    description="Find all functions that call a specific function"
)
async def find_callers(
    request: GraphQueryRequest,
    search_service: SearchService = Depends(get_search_service)
) -> dict[str, Any]:
    """
    Find all functions that call the specified function.

    Uses the knowledge graph to trace call relationships.

    Args:
        request: Query request with entity name

    Returns:
        List of calling functions with distances

    Example Request:
        {
            "repository_id": "...",
            "entity_name": "validate_email",
            "max_depth": 2
        }
    """
    try:
        results = await search_service.find_callers(
            entity_name=request.entity_name,
            repository_id=request.repository_id,
            max_depth=request.max_depth
        )
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/callees",
    response_model=dict[str, Any],
    summary="Find Callees",
    description="Find all functions called by a specific function"
)
async def find_callees(
    request: GraphQueryRequest,
    search_service: SearchService = Depends(get_search_service)
) -> dict[str, Any]:
    """
    Find all functions called by the specified function.

    Args:
        request: Query request with entity name

    Returns:
        List of called functions with distances
    """
    try:
        results = await search_service.find_callees(
            entity_name=request.entity_name,
            repository_id=request.repository_id,
            max_depth=request.max_depth
        )
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/dependencies",
    response_model=dict[str, Any],
    summary="Find Dependencies",
    description="Find all dependencies of an entity (calls, uses, imports)"
)
async def find_dependencies(
    request: GraphQueryRequest,
    search_service: SearchService = Depends(get_search_service)
) -> dict[str, Any]:
    """
    Find all dependencies of an entity.

    Includes CALLS, USES, and IMPORTS relationships.

    Args:
        request: Query request with entity name

    Returns:
        List of dependencies with relationship paths
    """
    try:
        results = await search_service.find_dependencies(
            entity_name=request.entity_name,
            repository_id=request.repository_id,
            max_depth=request.max_depth
        )
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/class-hierarchy",
    response_model=dict[str, Any],
    summary="Find Class Hierarchy",
    description="Get inheritance hierarchy for a class"
)
async def find_class_hierarchy(
    request: GraphQueryRequest,
    search_service: SearchService = Depends(get_search_service)
) -> dict[str, Any]:
    """
    Get the full inheritance hierarchy for a class.

    Returns both ancestors (parent classes) and
    descendants (child classes).

    Args:
        request: Query request with class name

    Returns:
        Hierarchy with ancestors and descendants
    """
    try:
        results = await search_service.find_class_hierarchy(
            class_name=request.entity_name,
            repository_id=request.repository_id
        )
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/similar",
    response_model=dict[str, Any],
    summary="Find Similar Code",
    description="Find code similar to a specific entity"
)
async def find_similar_code(
    repository_id: str,
    entity_id: str,
    limit: int = 10,
    exclude_same_file: bool = True,
    search_service: SearchService = Depends(get_search_service)
) -> dict[str, Any]:
    """
    Find code similar to a given entity.

    Uses vector embeddings to find semantically similar code.

    Args:
        repository_id: Repository UUID
        entity_id: Entity UUID to find similar code for
        limit: Maximum results
        exclude_same_file: Exclude entities from same file

    Returns:
        List of similar entities with similarity scores
    """
    try:
        results = await search_service.find_similar_code(
            entity_id=entity_id,
            repository_id=repository_id,
            limit=limit,
            exclude_same_file=exclude_same_file
        )
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/combined",
    response_model=dict[str, Any],
    summary="Combined Search",
    description="Run both semantic and structural search"
)
async def combined_search(
    request: SemanticSearchRequest,
    search_service: SearchService = Depends(get_search_service)
) -> dict[str, Any]:
    """
    Combined semantic and structural search.

    Runs both search types in parallel and merges results.

    Args:
        request: Search request

    Returns:
        Merged and ranked results from both sources
    """
    try:
        results = await search_service.combined_search(
            query=request.query,
            repository_id=request.repository_id,
            limit=request.limit,
            entity_types=request.entity_types
        )
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/overview/{repository_id}",
    response_model=dict[str, Any],
    summary="Repository Overview",
    description="Get overview statistics for a repository"
)
async def get_repository_overview(
    repository_id: str,
    search_service: SearchService = Depends(get_search_service)
) -> dict[str, Any]:
    """
    Get an overview of repository contents.

    Returns statistics about entities, relationships,
    and embeddings.

    Args:
        repository_id: Repository UUID

    Returns:
        Repository statistics
    """
    try:
        return await search_service.get_repository_overview(repository_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
