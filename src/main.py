"""
Main Application
================

FastAPI application entry point.
This is where everything comes together.

HOW THE APP STARTS:
    1. Create FastAPI app instance
    2. Register lifespan handler (startup/shutdown)
    3. On startup:
       - Initialize logging
       - Connect to Neo4j
       - Initialize ChromaDB
       - Create service instances
    4. Register API routes
    5. Start serving requests

LIFESPAN MANAGEMENT:
    The lifespan context manager handles:
    - Startup: Create and connect services
    - Shutdown: Clean up connections

RUNNING THE APP:
    # Development
    uvicorn src.main:app --reload

    # Production
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4

    # Or using the CLI script
    python -m src.main

API DOCUMENTATION:
    Once running, visit:
    - http://localhost:8000/docs     - Swagger UI
    - http://localhost:8000/redoc    - ReDoc
    - http://localhost:8000/openapi.json - OpenAPI spec
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.router import api_router
from src.core.config import settings
from src.core.exceptions import CodeIntelError
from src.core.logging import get_logger, setup_logging
from src.services.codeql_parser import CodeQLParser
from src.services.code_generator import CodeGenerator
from src.services.impact_analyzer import ImpactAnalyzer
from src.services.neo4j_service import Neo4jService
from src.services.repository_service import RepositoryService
from src.services.search_service import SearchService
from src.services.vector_service import VectorService
from src.services.cosmos_service import CosmosService
from src.services.chat_service import ChatService

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for startup and shutdown events.

    Startup:
        1. Setup logging
        2. Connect to Neo4j
        3. Initialize ChromaDB
        4. Create all service instances
        5. Store in app.state for dependency injection

    Shutdown:
        1. Close Neo4j connection
        2. Clean up any resources
    """
    # ==========================================================================
    # STARTUP
    # ==========================================================================
    logger.info("Starting Code Intelligence Backend...")

    # Setup logging
    setup_logging()

    # Initialize Neo4j
    logger.info("Connecting to Neo4j...")
    neo4j = Neo4jService()
    try:
        await neo4j.connect()
    except Exception as e:
        logger.warning(f"Neo4j connection failed: {e}. Running in degraded mode.")

    # Initialize Vector DB
    logger.info("Initializing Vector DB...")
    vector = VectorService()
    try:
        await vector.initialize()
    except Exception as e:
        logger.warning(f"Vector DB initialization failed: {e}. Running in degraded mode.")

    # Initialize CodeQL Parser
    logger.info("Initializing CodeQL Parser...")
    parser = CodeQLParser()

    # Initialize Cosmos DB (for chat conversations)
    logger.info("Initializing Cosmos DB...")
    cosmos = CosmosService()
    try:
        await cosmos.initialize()
    except Exception as e:
        logger.warning(f"Cosmos DB initialization failed: {e}. Chat features may be unavailable.")

    # Create services
    repository_service = RepositoryService(neo4j, vector, parser)
    search_service = SearchService(neo4j, vector)
    impact_analyzer = ImpactAnalyzer(neo4j, vector)
    code_generator = CodeGenerator(neo4j, vector)
    chat_service = ChatService(cosmos, neo4j, vector, code_generator)

    # Store in app.state for dependency injection
    app.state.neo4j = neo4j
    app.state.vector = vector
    app.state.parser = parser
    app.state.cosmos = cosmos
    app.state.repository_service = repository_service
    app.state.search_service = search_service
    app.state.impact_analyzer = impact_analyzer
    app.state.code_generator = code_generator
    app.state.chat_service = chat_service

    logger.info("Code Intelligence Backend started successfully!")

    yield  # App is running

    # ==========================================================================
    # SHUTDOWN
    # ==========================================================================
    logger.info("Shutting down Code Intelligence Backend...")

    # Close connections
    await neo4j.close()
    await cosmos.close()

    logger.info("Shutdown complete.")


# =============================================================================
# CREATE FASTAPI APP
# =============================================================================

app = FastAPI(
    title="Code Intelligence Backend",
    description="""
    ## Intelligent Code Analysis & Generation API

    This API provides powerful code intelligence features:

    ### Features

    * **Repository Analysis** - Analyze codebases to extract structure and relationships
    * **Semantic Search** - Find code using natural language queries
    * **Impact Analysis** - Understand the impact of code changes
    * **Code Generation** - Generate code following existing patterns
    * **Chat Conversations** - Interactive AI chat with code context

    ### Architecture

    * **Neo4j** - Knowledge graph for code relationships
    * **ChromaDB** - Vector database for semantic search
    * **Cosmos DB** - Conversation persistence
    * **CodeQL** - Code parsing and analysis
    * **LangChain** - LLM orchestration for code generation

    ### Quick Start

    1. Start the required services (Neo4j, Cosmos DB, configure OpenAI)
    2. Analyze a repository: `POST /api/v1/repositories`
    3. Search code: `POST /api/v1/search/semantic`
    4. Analyze impact: `POST /api/v1/impact/analyze`
    5. Generate code: `POST /api/v1/generate`
    6. Start a chat: `POST /api/v1/chat/conversations`
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# =============================================================================
# MIDDLEWARE
# =============================================================================

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(CodeIntelError)
async def code_intel_error_handler(
    request: Request,
    exc: CodeIntelError
) -> JSONResponse:
    """
    Handle custom CodeIntelError exceptions.

    Converts our custom exceptions to proper JSON responses.
    """
    return JSONResponse(
        status_code=400,
        content=exc.to_dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Logs the error and returns a generic error response.
    """
    logger.error(
        "Unexpected error",
        error=str(exc),
        path=request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": {"error": str(exc)} if settings.debug else {}
        }
    )


# =============================================================================
# ROUTES
# =============================================================================

# Include API router with /api/v1 prefix
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """
    Root endpoint - API information.
    """
    return {
        "name": "Code Intelligence Backend",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.api_workers
    )
