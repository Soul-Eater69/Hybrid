"""
API Dependencies
================

FastAPI dependency injection functions.
These provide service instances to API endpoints.

HOW DEPENDENCY INJECTION WORKS:
    1. Service instances are created when the app starts
    2. Dependencies are injected into endpoints via Depends()
    3. This allows for:
       - Single instance per service (singleton pattern)
       - Easy testing (can override dependencies)
       - Clean separation of concerns

USAGE IN ENDPOINTS:
    @router.get("/search")
    async def search(
        search_service: SearchService = Depends(get_search_service)
    ):
        return await search_service.search(...)

LIFECYCLE:
    App Startup
         ↓
    Create service instances (lifespan handler)
         ↓
    Store in app.state
         ↓
    Dependencies retrieve from app.state
         ↓
    Endpoints receive injected services
"""

from typing import Any

from fastapi import Request

from src.services.codeql_parser import CodeQLParser
from src.services.code_generator import CodeGenerator
from src.services.impact_analyzer import ImpactAnalyzer
from src.services.neo4j_service import Neo4jService
from src.services.repository_service import RepositoryService
from src.services.search_service import SearchService
from src.services.vector_service import VectorService
from src.services.chat_service import ChatService
from src.services.cosmos_service import CosmosService


# =============================================================================
# Service Dependencies
# =============================================================================

async def get_neo4j(request: Request) -> Neo4jService:
    """
    Get the Neo4j service instance.

    The Neo4j service is created during app startup and stored
    in app.state for reuse across requests.

    Args:
        request: FastAPI request (used to access app.state)

    Returns:
        Neo4jService instance
    """
    return request.app.state.neo4j


async def get_vector(request: Request) -> VectorService:
    """
    Get the Vector service instance.

    Args:
        request: FastAPI request

    Returns:
        VectorService instance
    """
    return request.app.state.vector


async def get_parser(request: Request) -> CodeQLParser:
    """
    Get the CodeQL parser instance.

    Args:
        request: FastAPI request

    Returns:
        CodeQLParser instance
    """
    return request.app.state.parser


async def get_repository_service(request: Request) -> RepositoryService:
    """
    Get the Repository service instance.

    Args:
        request: FastAPI request

    Returns:
        RepositoryService instance
    """
    return request.app.state.repository_service


async def get_search_service(request: Request) -> SearchService:
    """
    Get the Search service instance.

    Args:
        request: FastAPI request

    Returns:
        SearchService instance
    """
    return request.app.state.search_service


async def get_impact_analyzer(request: Request) -> ImpactAnalyzer:
    """
    Get the Impact Analyzer instance.

    Args:
        request: FastAPI request

    Returns:
        ImpactAnalyzer instance
    """
    return request.app.state.impact_analyzer


async def get_code_generator(request: Request) -> CodeGenerator:
    """
    Get the Code Generator instance.

    Args:
        request: FastAPI request

    Returns:
        CodeGenerator instance
    """
    return request.app.state.code_generator


async def get_cosmos(request: Request) -> CosmosService:
    """
    Get the Cosmos DB service instance.

    Args:
        request: FastAPI request

    Returns:
        CosmosService instance
    """
    return request.app.state.cosmos


async def get_chat_service(request: Request) -> ChatService:
    """
    Get the Chat service instance.

    Args:
        request: FastAPI request

    Returns:
        ChatService instance
    """
    return request.app.state.chat_service
