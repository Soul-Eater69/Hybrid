"""
Vector Database Service
=======================

Manages code embeddings in ChromaDB for semantic search.
This enables finding code by meaning, not just keywords.

WHAT ARE EMBEDDINGS?
    Embeddings are numerical representations of text that capture
    semantic meaning. Similar code produces similar embeddings.

    Example:
        "validate email address" → [0.23, -0.15, 0.87, ...]
        "check if email is valid" → [0.25, -0.12, 0.85, ...]
        These are similar vectors because they mean similar things!

WHY USE VECTOR SEARCH?
    Traditional search: Find "validate" in code
    Vector search: Find code that validates things (even if it
                   uses words like "check", "verify", "ensure")

HOW IT WORKS:
    1. Code entities are converted to text descriptions
    2. Text is sent to OpenAI embedding model
    3. Resulting vectors are stored in ChromaDB
    4. Queries are also converted to vectors
    5. ChromaDB finds the most similar code vectors

DATA FLOW:
    Code Entity
          ↓
    entity.to_embedding_document()
          ↓
    "# FUNCTION: validate_email\nFile: validators.py\n..."
          ↓
    OpenAI Embedding API
          ↓
    [0.23, -0.15, 0.87, ...] (1536 dimensions)
          ↓
    Stored in ChromaDB Collection

SEARCH FLOW:
    User Query: "function to check email validity"
          ↓
    OpenAI Embedding API
          ↓
    Query Vector: [0.21, -0.17, 0.89, ...]
          ↓
    ChromaDB similarity search
          ↓
    Top N most similar code entities

USAGE:
    from src.services.vector_service import VectorService

    vector_svc = VectorService()
    await vector_svc.initialize()

    # Store embeddings
    await vector_svc.store_entities(entities, repository_id)

    # Search
    results = await vector_svc.search("validate user input", limit=10)
"""

import asyncio
from typing import Any
from uuid import UUID

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_openai import OpenAIEmbeddings
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import settings
from src.core.exceptions import VectorDBError
from src.core.logging import LoggerMixin
from src.models.code_entity import CodeEntity


class VectorService(LoggerMixin):
    """
    Service for managing code embeddings in ChromaDB.

    Handles embedding generation, storage, and similarity search.

    Attributes:
        persist_directory: Where ChromaDB stores its data
        collection_name: Name of the embeddings collection
        embeddings: LangChain OpenAI embeddings instance
        client: ChromaDB client
        collection: ChromaDB collection
    """

    def __init__(self) -> None:
        """Initialize the vector service with configuration."""
        self.persist_directory = settings.chroma_persist_directory
        self.collection_name = settings.chroma_collection_name
        self._embeddings: OpenAIEmbeddings | None = None
        self._client: chromadb.Client | None = None
        self._collection: chromadb.Collection | None = None

    async def initialize(self) -> None:
        """
        Initialize ChromaDB client and OpenAI embeddings.

        Creates the collection if it doesn't exist.

        Raises:
            VectorDBError: If initialization fails
        """
        try:
            # Initialize OpenAI embeddings
            self._embeddings = OpenAIEmbeddings(
                model=settings.openai_embedding_model,
                openai_api_key=settings.openai_api_key
            )

            # Initialize ChromaDB with persistence
            self._client = chromadb.Client(ChromaSettings(
                persist_directory=self.persist_directory,
                anonymized_telemetry=False
            ))

            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Code entity embeddings"}
            )

            self.logger.info(
                "Vector service initialized",
                persist_directory=self.persist_directory,
                collection=self.collection_name
            )

        except Exception as e:
            self.logger.error("Failed to initialize vector service", error=str(e))
            raise VectorDBError(f"Initialization failed: {e}")

    @property
    def collection(self) -> chromadb.Collection:
        """Get the ChromaDB collection, raising if not initialized."""
        if not self._collection:
            raise VectorDBError("Vector service not initialized")
        return self._collection

    @property
    def embeddings(self) -> OpenAIEmbeddings:
        """Get the embeddings instance, raising if not initialized."""
        if not self._embeddings:
            raise VectorDBError("Vector service not initialized")
        return self._embeddings

    # =========================================================================
    # Storage Operations
    # =========================================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30)
    )
    async def store_entities(
        self,
        entities: list[CodeEntity],
        repository_id: str,
        batch_size: int = 100
    ) -> int:
        """
        Store code entities as embeddings in ChromaDB.

        Entities are batched to avoid overwhelming the embedding API.

        Args:
            entities: List of code entities to embed
            repository_id: ID of the repository
            batch_size: Number of entities per batch

        Returns:
            Number of entities stored

        Raises:
            VectorDBError: If storage fails
        """
        self.logger.info(
            "Storing entity embeddings",
            count=len(entities),
            repository_id=repository_id
        )

        stored_count = 0

        # Process in batches
        for i in range(0, len(entities), batch_size):
            batch = entities[i:i + batch_size]
            await self._store_batch(batch, repository_id)
            stored_count += len(batch)

            self.logger.debug(
                f"Stored batch {i // batch_size + 1}",
                stored=stored_count,
                total=len(entities)
            )

        self.logger.info(f"Stored {stored_count} entity embeddings")
        return stored_count

    async def _store_batch(
        self,
        entities: list[CodeEntity],
        repository_id: str
    ) -> None:
        """
        Store a batch of entities.

        Args:
            entities: Batch of entities
            repository_id: Repository ID
        """
        # Prepare documents for embedding
        documents = []
        ids = []
        metadatas = []

        for entity in entities:
            # Create document text for embedding
            doc_text = entity.to_embedding_document()
            documents.append(doc_text)

            # Use entity ID as ChromaDB ID
            ids.append(str(entity.id))

            # Store metadata for filtering
            metadatas.append({
                "repository_id": repository_id,
                "entity_type": entity.entity_type,
                "name": entity.name,
                "qualified_name": entity.qualified_name,
                "file_path": entity.file_path,
                "start_line": entity.start_line,
                "end_line": entity.end_line,
            })

        try:
            # Generate embeddings
            embedding_vectors = await asyncio.to_thread(
                self.embeddings.embed_documents,
                documents
            )

            # Store in ChromaDB
            self.collection.add(
                ids=ids,
                embeddings=embedding_vectors,
                documents=documents,
                metadatas=metadatas
            )

        except Exception as e:
            self.logger.error("Failed to store embedding batch", error=str(e))
            raise VectorDBError(f"Batch storage failed: {e}")

    # =========================================================================
    # Search Operations
    # =========================================================================

    async def search(
        self,
        query: str,
        repository_id: str | None = None,
        limit: int = 10,
        entity_types: list[str] | None = None,
        file_pattern: str | None = None,
        min_score: float = 0.0
    ) -> list[dict[str, Any]]:
        """
        Search for code entities by semantic similarity.

        Finds code that is semantically similar to the query,
        even if it uses different words.

        Args:
            query: Natural language search query
            repository_id: Filter by repository (optional)
            limit: Maximum results to return
            entity_types: Filter by entity types (optional)
            file_pattern: Glob pattern for file filtering (optional)
            min_score: Minimum similarity score (0-1)

        Returns:
            List of search results with entity info and scores

        Example:
            results = await vector_svc.search(
                query="function that validates user input",
                repository_id="repo-123",
                limit=5,
                entity_types=["function"]
            )
            # Returns functions related to input validation
        """
        self.logger.info(
            "Performing semantic search",
            query=query[:100],
            repository_id=repository_id,
            limit=limit
        )

        try:
            # Generate query embedding
            query_embedding = await asyncio.to_thread(
                self.embeddings.embed_query,
                query
            )

            # Build filter conditions
            where_filter = self._build_filter(
                repository_id,
                entity_types,
                file_pattern
            )

            # Execute search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter if where_filter else None,
                include=["documents", "metadatas", "distances"]
            )

            # Process results
            search_results = []
            if results["ids"] and results["ids"][0]:
                for i, entity_id in enumerate(results["ids"][0]):
                    # ChromaDB returns distances, convert to similarity score
                    # For L2 distance, similarity = 1 / (1 + distance)
                    distance = results["distances"][0][i] if results["distances"] else 0
                    score = 1 / (1 + distance)

                    if score < min_score:
                        continue

                    search_results.append({
                        "entity_id": entity_id,
                        "score": score,
                        "document": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
                    })

            self.logger.info(f"Search returned {len(search_results)} results")
            return search_results

        except Exception as e:
            self.logger.error("Search failed", error=str(e))
            raise VectorDBError(f"Search failed: {e}")

    def _build_filter(
        self,
        repository_id: str | None,
        entity_types: list[str] | None,
        file_pattern: str | None
    ) -> dict[str, Any] | None:
        """
        Build ChromaDB filter from parameters.

        Args:
            repository_id: Repository filter
            entity_types: Entity type filter
            file_pattern: File pattern filter

        Returns:
            ChromaDB where clause dict or None
        """
        conditions = []

        if repository_id:
            conditions.append({"repository_id": {"$eq": repository_id}})

        if entity_types:
            if len(entity_types) == 1:
                conditions.append({"entity_type": {"$eq": entity_types[0]}})
            else:
                conditions.append({"entity_type": {"$in": entity_types}})

        # Note: file_pattern would need regex which ChromaDB doesn't support
        # For now, exact file path matching
        if file_pattern and "*" not in file_pattern:
            conditions.append({"file_path": {"$eq": file_pattern}})

        if not conditions:
            return None
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}

    async def find_similar(
        self,
        entity_id: str,
        limit: int = 10,
        exclude_same_file: bool = False
    ) -> list[dict[str, Any]]:
        """
        Find entities similar to a given entity.

        Useful for finding related code or potential duplicates.

        Args:
            entity_id: ID of the entity to find similar ones for
            limit: Maximum results
            exclude_same_file: If True, exclude entities from same file

        Returns:
            List of similar entities with scores
        """
        try:
            # Get the entity's embedding
            result = self.collection.get(
                ids=[entity_id],
                include=["embeddings", "metadatas"]
            )

            if not result["embeddings"]:
                self.logger.warning(f"Entity {entity_id} not found in vector DB")
                return []

            entity_embedding = result["embeddings"][0]
            entity_metadata = result["metadatas"][0] if result["metadatas"] else {}

            # Build filter to exclude the entity itself
            where_filter: dict[str, Any] = {}
            if exclude_same_file and "file_path" in entity_metadata:
                where_filter = {
                    "file_path": {"$ne": entity_metadata["file_path"]}
                }

            # Search for similar
            results = self.collection.query(
                query_embeddings=[entity_embedding],
                n_results=limit + 1,  # +1 because it might include itself
                where=where_filter if where_filter else None,
                include=["documents", "metadatas", "distances"]
            )

            # Process results, excluding the entity itself
            search_results = []
            if results["ids"] and results["ids"][0]:
                for i, eid in enumerate(results["ids"][0]):
                    if eid == entity_id:
                        continue

                    distance = results["distances"][0][i] if results["distances"] else 0
                    score = 1 / (1 + distance)

                    search_results.append({
                        "entity_id": eid,
                        "score": score,
                        "document": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
                    })

                    if len(search_results) >= limit:
                        break

            return search_results

        except Exception as e:
            self.logger.error("Find similar failed", error=str(e))
            raise VectorDBError(f"Find similar failed: {e}")

    # =========================================================================
    # Management Operations
    # =========================================================================

    async def delete_repository(self, repository_id: str) -> int:
        """
        Delete all embeddings for a repository.

        Args:
            repository_id: ID of the repository

        Returns:
            Number of embeddings deleted
        """
        try:
            # Get all IDs for this repository
            results = self.collection.get(
                where={"repository_id": {"$eq": repository_id}},
                include=[]
            )

            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                deleted_count = len(results["ids"])
                self.logger.info(
                    "Deleted repository embeddings",
                    repository_id=repository_id,
                    count=deleted_count
                )
                return deleted_count

            return 0

        except Exception as e:
            self.logger.error(
                "Failed to delete repository embeddings",
                error=str(e)
            )
            raise VectorDBError(f"Delete failed: {e}")

    async def get_stats(self) -> dict[str, Any]:
        """
        Get vector database statistics.

        Returns:
            Dict with collection stats
        """
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "total_embeddings": count,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            self.logger.error("Failed to get stats", error=str(e))
            return {"error": str(e)}

    async def health_check(self) -> bool:
        """
        Check if vector service is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to get collection count
            self.collection.count()
            return True
        except Exception as e:
            self.logger.error("Vector service health check failed", error=str(e))
            return False
