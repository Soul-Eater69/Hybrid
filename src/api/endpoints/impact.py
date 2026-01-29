"""
Impact Analysis Endpoints
=========================

Endpoints for analyzing the impact of code changes.

PURPOSE:
    Answer the question: "If I change this code, what else might break?"

ENDPOINTS:
    POST /impact/analyze    - Analyze impact of a change

DATA FLOW:
    Change Request
          ↓
    ImpactAnalyzer.analyze()
          ↓
    Neo4j Graph Traversal
          ↓
    Impact Scoring
          ↓
    Recommendations

USAGE:
    curl -X POST http://localhost:8000/api/v1/impact/analyze \\
         -H "Content-Type: application/json" \\
         -d '{
             "repository_id": "...",
             "entity_name": "validate_email",
             "change_description": "Changing return type"
         }'
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any

from src.api.dependencies import get_impact_analyzer
from src.schemas.requests import ImpactAnalysisRequest
from src.schemas.responses import ImpactAnalysisResponse, ErrorResponse
from src.services.impact_analyzer import ImpactAnalyzer

router = APIRouter()


@router.post(
    "/analyze",
    response_model=dict[str, Any],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Analysis failed"}
    },
    summary="Analyze Change Impact",
    description="Analyze the potential impact of changing a code entity"
)
async def analyze_impact(
    request: ImpactAnalysisRequest,
    analyzer: ImpactAnalyzer = Depends(get_impact_analyzer)
) -> dict[str, Any]:
    """
    Analyze the impact of changing a code entity.

    This endpoint:
    1. Identifies the entity being changed
    2. Traverses the knowledge graph to find dependents
    3. Calculates impact scores for each dependent
    4. Generates recommendations

    Args:
        request: Impact analysis request
        analyzer: Impact analyzer service

    Returns:
        Impact analysis results with affected entities

    Example Request:
        {
            "repository_id": "550e8400-e29b-41d4-a716-446655440000",
            "entity_name": "validate_email",
            "change_description": "Changing return type from bool to ValidationResult",
            "change_type": "signature_change",
            "max_depth": 3
        }

    Example Response:
        {
            "id": "...",
            "source_entity": {...},
            "impacted_entities": [
                {
                    "entity_name": "register_user",
                    "impact_level": "critical",
                    "impact_score": 9.0,
                    "reason": "Directly calls validate_email"
                },
                ...
            ],
            "summary": {...},
            "recommendations": [...]
        }
    """
    try:
        impact = await analyzer.analyze(
            repository_id=request.repository_id,
            entity_id=request.entity_id,
            entity_name=request.entity_name,
            file_path=request.file_path,
            change_description=request.change_description,
            change_type=request.change_type,
            max_depth=request.max_depth
        )

        # Convert to response format
        return {
            "id": str(impact.id),
            "source_entity": {
                "id": str(impact.source_entity_id),
                "name": impact.source_entity_name,
                "file_path": impact.source_file_path
            },
            "impacted_entities": [
                {
                    "entity_id": str(e.entity_id),
                    "entity_name": e.entity_name,
                    "entity_type": e.entity_type,
                    "file_path": e.file_path,
                    "impact_level": e.impact_level,
                    "impact_score": e.impact_score,
                    "distance": e.distance,
                    "relationship_path": e.relationship_path,
                    "reason": e.reason,
                    "suggested_action": e.suggested_action
                }
                for e in impact.impacted_entities
            ],
            "summary": {
                "total_count": impact.total_count,
                "critical_count": impact.critical_count,
                "direct_count": impact.direct_count,
                "indirect_count": impact.indirect_count,
                "total_impact_score": impact.total_impact_score,
                "max_depth": impact.max_depth
            },
            "recommendations": impact.recommendations,
            "summary_text": impact.summary,
            "created_at": impact.created_at.isoformat()
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/summary",
    response_model=dict[str, Any],
    summary="Get Change Summary",
    description="Get a structured summary of impact analysis"
)
async def get_change_summary(
    request: ImpactAnalysisRequest,
    analyzer: ImpactAnalyzer = Depends(get_impact_analyzer)
) -> dict[str, Any]:
    """
    Get a structured summary of the impact analysis.

    Provides a more concise view of the impact, grouped by file.

    Args:
        request: Impact analysis request

    Returns:
        Structured summary
    """
    try:
        impact = await analyzer.analyze(
            repository_id=request.repository_id,
            entity_id=request.entity_id,
            entity_name=request.entity_name,
            file_path=request.file_path,
            change_description=request.change_description,
            change_type=request.change_type,
            max_depth=request.max_depth
        )

        return await analyzer.get_change_summary(impact)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
