"""
API Router Configuration
========================

Configures all API routes and their prefixes.

ROUTE STRUCTURE:
    /api/v1
    ├── /health          - Health check endpoints
    ├── /repositories    - Repository management
    │   ├── POST /       - Analyze a repository
    │   ├── GET /        - List repositories
    │   ├── GET /{id}    - Get repository details
    │   └── DELETE /{id} - Delete repository
    ├── /search          - Code search
    │   ├── POST /semantic    - Semantic search
    │   ├── POST /callers     - Find callers
    │   ├── POST /callees     - Find callees
    │   └── POST /similar     - Find similar code
    ├── /impact          - Impact analysis
    │   └── POST /analyze     - Analyze change impact
    ├── /generate        - Code generation
    │   └── POST /       - Generate code
    └── /chat            - Chat conversations
        ├── POST /conversations           - Create conversation
        ├── GET /conversations            - List conversations
        ├── GET /conversations/{id}       - Get conversation
        ├── DELETE /conversations/{id}    - Delete conversation
        └── POST /conversations/{id}/messages - Send message
"""

from fastapi import APIRouter

from src.api.endpoints import health, repositories, search, impact, generate, chat

# Main API router
api_router = APIRouter()

# Include all routers with their prefixes
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"]
)

api_router.include_router(
    repositories.router,
    prefix="/repositories",
    tags=["Repositories"]
)

api_router.include_router(
    search.router,
    prefix="/search",
    tags=["Search"]
)

api_router.include_router(
    impact.router,
    prefix="/impact",
    tags=["Impact Analysis"]
)

api_router.include_router(
    generate.router,
    prefix="/generate",
    tags=["Code Generation"]
)

api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["Chat"]
)
