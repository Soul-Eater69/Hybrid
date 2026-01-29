"""
Code Generation Endpoints
=========================

Endpoints for AI-powered code generation.

PURPOSE:
    Generate code that follows existing patterns in the codebase
    using RAG (Retrieval Augmented Generation).

ENDPOINTS:
    POST /generate          - Generate code from prompt
    POST /generate/improve  - Suggest improvements for code

DATA FLOW:
    User Prompt
          ↓
    Retrieve Similar Code (Vector DB)
          ↓
    Get Related Entities (Neo4j)
          ↓
    Build Context
          ↓
    LLM Generation
          ↓
    Generated Code + Explanation

USAGE:
    curl -X POST http://localhost:8000/api/v1/generate \\
         -H "Content-Type: application/json" \\
         -d '{
             "repository_id": "...",
             "prompt": "Create a function to validate phone numbers",
             "include_tests": true
         }'
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Any

from src.api.dependencies import get_code_generator
from src.schemas.requests import CodeGenerationRequest
from src.schemas.responses import CodeGenerationResponse, ErrorResponse
from src.services.code_generator import CodeGenerator

router = APIRouter()


@router.post(
    "",
    response_model=dict[str, Any],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Generation failed"}
    },
    summary="Generate Code",
    description="Generate code based on natural language prompt and codebase context"
)
async def generate_code(
    request: CodeGenerationRequest,
    generator: CodeGenerator = Depends(get_code_generator)
) -> dict[str, Any]:
    """
    Generate code using AI with codebase context.

    This endpoint:
    1. Searches for similar code in the codebase
    2. Gets related entities from the knowledge graph
    3. Builds context from examples and relationships
    4. Uses LLM to generate code following existing patterns
    5. Optionally generates tests

    Args:
        request: Code generation request
        generator: Code generator service

    Returns:
        Generated code with explanation and metadata

    Example Request:
        {
            "repository_id": "550e8400-e29b-41d4-a716-446655440000",
            "prompt": "Create a function to validate phone numbers",
            "context_entities": ["validate_email", "validate_username"],
            "target_file": "src/validators/phone.py",
            "include_tests": true
        }

    Example Response:
        {
            "id": "...",
            "prompt": "Create a function to validate phone numbers",
            "generated": {
                "code": "def validate_phone(phone: str) -> bool: ...",
                "explanation": "This function validates phone numbers...",
                "tests": "def test_validate_phone(): ...",
                "confidence_score": 0.85
            }
        }
    """
    try:
        result = await generator.generate(
            repository_id=request.repository_id,
            prompt=request.prompt,
            context_entities=request.context_entities,
            target_file=request.target_file,
            similar_code_count=request.similar_code_count,
            include_tests=request.include_tests,
            style_guide=request.style_guide
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/improve",
    response_model=dict[str, Any],
    summary="Suggest Improvements",
    description="Get AI suggestions for improving existing code"
)
async def suggest_improvements(
    repository_id: str,
    code: str,
    generator: CodeGenerator = Depends(get_code_generator)
) -> dict[str, Any]:
    """
    Get AI suggestions for improving code.

    Analyzes the code and suggests improvements based on:
    - Code quality and readability
    - Error handling
    - Performance
    - Best practices

    Args:
        repository_id: Repository UUID
        code: Code to analyze
        generator: Code generator service

    Returns:
        Improvement suggestions

    Example Request:
        {
            "repository_id": "...",
            "code": "def foo(x):\\n    return x + 1"
        }
    """
    try:
        result = await generator.suggest_improvements(
            code=code,
            repository_id=repository_id
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
