"""
Schemas Module
==============

Defines API request and response schemas using Pydantic.
These schemas are used for FastAPI endpoint validation and documentation.

Components:
    - requests: Input schemas for API endpoints
    - responses: Output schemas for API responses
"""

from src.schemas.requests import (
    AnalyzeRepositoryRequest,
    ImpactAnalysisRequest,
    CodeGenerationRequest,
    SemanticSearchRequest,
)
from src.schemas.responses import (
    RepositoryResponse,
    ImpactAnalysisResponse,
    CodeGenerationResponse,
    SemanticSearchResponse,
    EntityResponse,
    HealthResponse,
    ErrorResponse,
)

__all__ = [
    # Requests
    "AnalyzeRepositoryRequest",
    "ImpactAnalysisRequest",
    "CodeGenerationRequest",
    "SemanticSearchRequest",
    # Responses
    "RepositoryResponse",
    "ImpactAnalysisResponse",
    "CodeGenerationResponse",
    "SemanticSearchResponse",
    "EntityResponse",
    "HealthResponse",
    "ErrorResponse",
]
