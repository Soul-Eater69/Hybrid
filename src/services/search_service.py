"""
Search Service
==============

Provides unified code search across both vector and graph databases.
Combines semantic search with structural queries.

SEARCH TYPES:
    1. Semantic Search: Find code by meaning (Vector DB)
    2. Structural Search: Find by relationships (Neo4j)
    3. Combined Search: Merge results from both

HOW IT WORKS:
    Semantic Search:
        User Query → Embedding → Vector Similarity → Results

    Structural Search:
        User Query → Pattern Matching → Graph Traversal → Results

    Combined Search:
        Both searches in parallel → Merge & Rank → Final Results

DATA FLOW:
    Search Request
          ↓
    ┌──────┴──────┐
    ↓             ↓
    Vector DB   Neo4j
    (semantic)  (structural)
    ↓             ↓
    └──────┬──────┘
          ↓
    Merge Results
          ↓
    Rank by Relevance
          ↓
    Search Response

USAGE:
    from src.services.search_service import SearchService

    search = SearchService(neo4j, vector_svc)

    # Semantic search
    results = await search.semantic_search(
        query="validate user input",
        repository_id="repo-123"
    )

    # Structural search
    results = await search.find_callers(
        entity_name="process_data",
        repository_id="repo-123"
    )

    # Combined search
    results = await search.combined_search(
        query="authentication handler",
        repository_id="repo-123"
    )
"""

import asyncio
from typing import Any

from src.core.logging import LoggerMixin
from src.services.neo4j_service import Neo4jService
from src.services.vector_service import VectorService


class SearchService(LoggerMixin):
    """
    Unified search service for code discovery.

    Combines vector similarity search with graph-based
    structural queries.

    Attributes:
        neo4j: Neo4j service for graph queries
        vector: Vector service for semantic search
    """

    def __init__(
        self,
        neo4j: Neo4jService,
        vector: VectorService
    ) -> None:
        """
        Initialize the search service.

        Args:
            neo4j: Neo4j service instance
            vector: Vector service instance
        """
        self.neo4j = neo4j
        self.vector = vector

    # =========================================================================
    # Semantic Search (Vector DB)
    # =========================================================================

    async def semantic_search(
        self,
        query: str,
        repository_id: str,
        limit: int = 10,
        entity_types: list[str] | None = None,
        file_pattern: str | None = None,
        min_score: float = 0.0
    ) -> dict[str, Any]:
        """
        Search for code using natural language semantics.

        Finds code that is semantically similar to the query,
        even if it uses different words.

        Args:
            query: Natural language search query
            repository_id: UUID of the repository
            limit: Maximum number of results
            entity_types: Filter by types (function, class, module)
            file_pattern: Filter by file path pattern
            min_score: Minimum similarity score (0-1)

        Returns:
            Search results with entities and scores

        Example:
            results = await search.semantic_search(
                query="function to validate email addresses",
                repository_id="repo-123",
                entity_types=["function"]
            )
        """
        self.logger.info(
            "Performing semantic search",
            query=query[:50],
            repository_id=repository_id
        )

        # Search vector DB
        vector_results = await self.vector.search(
            query=query,
            repository_id=repository_id,
            limit=limit,
            entity_types=entity_types,
            file_pattern=file_pattern,
            min_score=min_score
        )

        # Enhance results with Neo4j data
        enhanced_results = []
        for result in vector_results:
            entity_id = result["entity_id"]
            entity_data = await self.neo4j.get_entity_by_id(entity_id)

            if entity_data:
                enhanced_results.append({
                    "entity": {
                        "id": entity_data["id"],
                        "name": entity_data["name"],
                        "qualified_name": entity_data.get("qualified_name", ""),
                        "entity_type": entity_data.get("entity_type", ""),
                        "file_path": entity_data["file_path"],
                        "start_line": entity_data.get("start_line", 0),
                        "end_line": entity_data.get("end_line", 0),
                        "docstring": entity_data.get("docstring"),
                        "signature": entity_data.get("signature"),
                    },
                    "score": result["score"],
                    "snippet": result.get("document", "")[:500]
                })

        return {
            "query": query,
            "results": enhanced_results,
            "total_count": len(enhanced_results),
            "search_type": "semantic"
        }

    # =========================================================================
    # Structural Search (Neo4j)
    # =========================================================================

    async def find_callers(
        self,
        entity_name: str,
        repository_id: str,
        max_depth: int = 2
    ) -> dict[str, Any]:
        """
        Find all functions that call a specific function.

        Uses the CALLS relationship in the knowledge graph.

        Args:
            entity_name: Name of the function
            repository_id: UUID of the repository
            max_depth: Maximum call chain depth

        Returns:
            List of calling functions
        """
        self.logger.info(
            "Finding callers",
            entity_name=entity_name,
            repository_id=repository_id
        )

        # First, find the entity
        entity = await self.neo4j.get_entity_by_name(
            entity_name,
            repository_id
        )

        if not entity:
            return {
                "entity_name": entity_name,
                "results": [],
                "total_count": 0,
                "message": "Entity not found"
            }

        # Get callers
        callers = await self.neo4j.get_callers(
            entity["id"],
            max_depth=max_depth
        )

        return {
            "entity_name": entity_name,
            "entity_id": entity["id"],
            "results": [
                {
                    "entity": c["entity"],
                    "distance": c["distance"]
                }
                for c in callers
            ],
            "total_count": len(callers),
            "search_type": "callers"
        }

    async def find_callees(
        self,
        entity_name: str,
        repository_id: str,
        max_depth: int = 2
    ) -> dict[str, Any]:
        """
        Find all functions called by a specific function.

        Args:
            entity_name: Name of the function
            repository_id: UUID of the repository
            max_depth: Maximum call chain depth

        Returns:
            List of called functions
        """
        self.logger.info(
            "Finding callees",
            entity_name=entity_name,
            repository_id=repository_id
        )

        # First, find the entity
        entity = await self.neo4j.get_entity_by_name(
            entity_name,
            repository_id
        )

        if not entity:
            return {
                "entity_name": entity_name,
                "results": [],
                "total_count": 0,
                "message": "Entity not found"
            }

        # Get callees
        callees = await self.neo4j.get_callees(
            entity["id"],
            max_depth=max_depth
        )

        return {
            "entity_name": entity_name,
            "entity_id": entity["id"],
            "results": [
                {
                    "entity": c["entity"],
                    "distance": c["distance"]
                }
                for c in callees
            ],
            "total_count": len(callees),
            "search_type": "callees"
        }

    async def find_dependencies(
        self,
        entity_name: str,
        repository_id: str,
        max_depth: int = 2
    ) -> dict[str, Any]:
        """
        Find all dependencies of a specific entity.

        Includes CALLS, USES, and IMPORTS relationships.

        Args:
            entity_name: Name of the entity
            repository_id: UUID of the repository
            max_depth: Maximum traversal depth

        Returns:
            List of dependencies
        """
        entity = await self.neo4j.get_entity_by_name(
            entity_name,
            repository_id
        )

        if not entity:
            return {
                "entity_name": entity_name,
                "results": [],
                "total_count": 0,
                "message": "Entity not found"
            }

        dependencies = await self.neo4j.get_dependencies(
            entity["id"],
            max_depth=max_depth
        )

        return {
            "entity_name": entity_name,
            "entity_id": entity["id"],
            "results": dependencies,
            "total_count": len(dependencies),
            "search_type": "dependencies"
        }

    async def find_class_hierarchy(
        self,
        class_name: str,
        repository_id: str
    ) -> dict[str, Any]:
        """
        Find the inheritance hierarchy for a class.

        Args:
            class_name: Name of the class
            repository_id: UUID of the repository

        Returns:
            Hierarchy with ancestors and descendants
        """
        entity = await self.neo4j.get_entity_by_name(
            class_name,
            repository_id
        )

        if not entity:
            return {
                "class_name": class_name,
                "hierarchy": {},
                "message": "Class not found"
            }

        hierarchy = await self.neo4j.get_class_hierarchy(entity["id"])

        return {
            "class_name": class_name,
            "class_id": entity["id"],
            "hierarchy": hierarchy,
            "search_type": "class_hierarchy"
        }

    # =========================================================================
    # Combined Search
    # =========================================================================

    async def combined_search(
        self,
        query: str,
        repository_id: str,
        limit: int = 10,
        entity_types: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Perform combined semantic and structural search.

        Runs both searches in parallel and merges results.

        Args:
            query: Search query (natural language)
            repository_id: UUID of the repository
            limit: Maximum results per search type
            entity_types: Filter by entity types

        Returns:
            Combined search results
        """
        self.logger.info(
            "Performing combined search",
            query=query[:50],
            repository_id=repository_id
        )

        # Run searches in parallel
        semantic_task = self.semantic_search(
            query=query,
            repository_id=repository_id,
            limit=limit,
            entity_types=entity_types
        )

        # For structural, try to find entity names in the query
        # This is a simple heuristic - could be improved with NLP
        words = query.split()
        potential_entities = [
            w for w in words
            if w[0].isupper() or '_' in w
        ]

        structural_results = []
        if potential_entities:
            for entity_name in potential_entities[:3]:  # Limit checks
                try:
                    callers = await self.find_callers(
                        entity_name=entity_name,
                        repository_id=repository_id,
                        max_depth=1
                    )
                    if callers["results"]:
                        structural_results.extend(callers["results"])
                except Exception:
                    pass

        # Get semantic results
        semantic_results = await semantic_task

        # Merge and deduplicate
        seen_ids = set()
        merged_results = []

        # Add semantic results first (higher priority)
        for result in semantic_results["results"]:
            entity_id = result["entity"]["id"]
            if entity_id not in seen_ids:
                seen_ids.add(entity_id)
                merged_results.append({
                    **result,
                    "source": "semantic"
                })

        # Add structural results
        for result in structural_results:
            entity_id = result["entity"]["id"]
            if entity_id not in seen_ids:
                seen_ids.add(entity_id)
                merged_results.append({
                    "entity": result["entity"],
                    "score": 1.0 / (1 + result["distance"]),  # Convert distance to score
                    "source": "structural"
                })

        return {
            "query": query,
            "results": merged_results[:limit],
            "total_count": len(merged_results),
            "search_type": "combined"
        }

    # =========================================================================
    # Similar Code
    # =========================================================================

    async def find_similar_code(
        self,
        entity_id: str,
        repository_id: str,
        limit: int = 10,
        exclude_same_file: bool = True
    ) -> dict[str, Any]:
        """
        Find code similar to a specific entity.

        Useful for:
        - Finding duplicate or near-duplicate code
        - Finding related implementations
        - Suggesting refactoring opportunities

        Args:
            entity_id: UUID of the entity
            repository_id: UUID of the repository
            limit: Maximum results
            exclude_same_file: Exclude entities from same file

        Returns:
            List of similar entities
        """
        self.logger.info(
            "Finding similar code",
            entity_id=entity_id
        )

        # Get entity info
        entity = await self.neo4j.get_entity_by_id(entity_id)
        if not entity:
            return {
                "entity_id": entity_id,
                "results": [],
                "message": "Entity not found"
            }

        # Find similar in vector DB
        similar = await self.vector.find_similar(
            entity_id=entity_id,
            limit=limit,
            exclude_same_file=exclude_same_file
        )

        # Enhance with Neo4j data
        enhanced_results = []
        for result in similar:
            similar_entity = await self.neo4j.get_entity_by_id(
                result["entity_id"]
            )
            if similar_entity:
                enhanced_results.append({
                    "entity": similar_entity,
                    "similarity_score": result["score"]
                })

        return {
            "source_entity": entity,
            "results": enhanced_results,
            "total_count": len(enhanced_results),
            "search_type": "similar_code"
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_repository_overview(
        self,
        repository_id: str
    ) -> dict[str, Any]:
        """
        Get an overview of a repository's indexed content.

        Args:
            repository_id: UUID of the repository

        Returns:
            Repository statistics and overview
        """
        # Get stats from Neo4j
        neo4j_stats = await self.neo4j.get_repository_stats(repository_id)

        # Get stats from vector DB
        vector_stats = await self.vector.get_stats()

        return {
            "repository_id": repository_id,
            "entities": {
                "total": neo4j_stats.get("total_entities", 0),
                "functions": neo4j_stats.get("functions", 0),
                "classes": neo4j_stats.get("classes", 0),
                "modules": neo4j_stats.get("modules", 0)
            },
            "relationships": neo4j_stats.get("relationships", {}),
            "embeddings": vector_stats.get("total_embeddings", 0)
        }
