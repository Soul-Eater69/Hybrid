"""
Services Module
===============

Contains all business logic services for the Code Intelligence Backend.

ARCHITECTURE OVERVIEW:
    The services are organized in a layered architecture:

    ┌─────────────────────────────────────────────────────────────┐
    │                      API Layer (FastAPI)                     │
    └─────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                    Orchestration Services                    │
    │  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐  │
    │  │ ImpactAnalyzer  │  │ CodeGenerator    │  │ SearchSvc  │  │
    │  └────────┬────────┘  └────────┬─────────┘  └─────┬──────┘  │
    └───────────┼─────────────────────┼──────────────────┼─────────┘
                │                     │                  │
                ▼                     ▼                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                      Storage Services                        │
    │  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐  │
    │  │ Neo4jService    │  │ VectorDBService  │  │ RepoSvc    │  │
    │  │ (graph store)   │  │ (embeddings)     │  │ (git ops)  │  │
    │  └────────┬────────┘  └────────┬─────────┘  └─────┬──────┘  │
    └───────────┼─────────────────────┼──────────────────┼─────────┘
                │                     │                  │
                ▼                     ▼                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                      Analysis Services                       │
    │  ┌─────────────────────────────────────────────────────────┐ │
    │  │              CodeQLParser (code analysis)                │ │
    │  └─────────────────────────────────────────────────────────┘ │
    └─────────────────────────────────────────────────────────────┘

Services:
    - codeql_parser: Parses code using CodeQL to extract entities
    - neo4j_service: Manages the knowledge graph in Neo4j
    - vector_service: Manages embeddings in ChromaDB
    - repository_service: Handles git operations and repo management
    - impact_analyzer: Analyzes code change impact
    - code_generator: Generates code using LangChain and LLM
    - search_service: Semantic code search
    - guardrails: Input/output validation and safety checks
    - context_aggregator: Combines context from multiple sources
    - chat_service: Orchestrates chat conversations
    - cosmos_service: Manages Cosmos DB persistence
"""

from src.services.codeql_parser import CodeQLParser
from src.services.neo4j_service import Neo4jService
from src.services.vector_service import VectorService
from src.services.repository_service import RepositoryService
from src.services.impact_analyzer import ImpactAnalyzer
from src.services.code_generator import CodeGenerator
from src.services.search_service import SearchService
from src.services.guardrails import Guardrails, GuardrailConfig, GuardrailResult
from src.services.context_aggregator import ContextAggregator, ContextConfig, AggregatedContext
from src.services.chat_service import ChatService
from src.services.cosmos_service import CosmosService

__all__ = [
    "CodeQLParser",
    "Neo4jService",
    "VectorService",
    "RepositoryService",
    "ImpactAnalyzer",
    "CodeGenerator",
    "SearchService",
    "Guardrails",
    "GuardrailConfig",
    "GuardrailResult",
    "ContextAggregator",
    "ContextConfig",
    "AggregatedContext",
    "ChatService",
    "CosmosService",
]
