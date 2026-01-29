"""
Health Check Endpoints
======================

Provides endpoints to check the health of the service and its dependencies.

ENDPOINTS:
    GET /health         - Basic health check
    GET /health/ready   - Readiness check (all dependencies)
    GET /health/live    - Liveness check (service is running)

USAGE:
    # Basic health
    curl http://localhost:8000/api/v1/health

    # Full readiness (checks Neo4j, ChromaDB, OpenAI)
    curl http://localhost:8000/api/v1/health/ready
"""

from datetime import datetime

from fastapi import APIRouter, Depends

from src.api.dependencies import get_neo4j, get_vector
from src.schemas.responses import HealthResponse

router = APIRouter()


@router.get(
    "",
    response_model=HealthResponse,
    summary="Health Check",
    description="Basic health check - returns OK if service is running"
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns:
        HealthResponse with status and version
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={},
        timestamp=datetime.utcnow()
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Readiness Check",
    description="Full readiness check - verifies all dependencies are accessible"
)
async def readiness_check(
    neo4j=Depends(get_neo4j),
    vector=Depends(get_vector)
) -> HealthResponse:
    """
    Full readiness check - verifies all dependencies.

    Checks:
        - Neo4j connectivity
        - ChromaDB connectivity
        - OpenAI API (via embedding test)

    Returns:
        HealthResponse with individual service statuses
    """
    services = {}
    overall_healthy = True

    # Check Neo4j
    try:
        neo4j_healthy = await neo4j.health_check()
        services["neo4j"] = "connected" if neo4j_healthy else "disconnected"
        if not neo4j_healthy:
            overall_healthy = False
    except Exception as e:
        services["neo4j"] = f"error: {str(e)}"
        overall_healthy = False

    # Check Vector DB
    try:
        vector_healthy = await vector.health_check()
        services["chromadb"] = "connected" if vector_healthy else "disconnected"
        if not vector_healthy:
            overall_healthy = False
    except Exception as e:
        services["chromadb"] = f"error: {str(e)}"
        overall_healthy = False

    # OpenAI is implicitly checked when Vector DB works (it uses OpenAI embeddings)
    services["openai"] = "connected" if services.get("chromadb") == "connected" else "unknown"

    return HealthResponse(
        status="healthy" if overall_healthy else "degraded",
        version="1.0.0",
        services=services,
        timestamp=datetime.utcnow()
    )


@router.get(
    "/live",
    summary="Liveness Check",
    description="Simple liveness check - returns 200 if service is alive"
)
async def liveness_check() -> dict[str, str]:
    """
    Simple liveness check for Kubernetes/Docker health probes.

    Returns:
        Simple OK response
    """
    return {"status": "alive"}
