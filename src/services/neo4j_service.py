"""
Neo4j Knowledge Graph Service
=============================

Manages the code knowledge graph stored in Neo4j.
This service handles all graph database operations.

WHAT IS A KNOWLEDGE GRAPH?
    A knowledge graph stores data as nodes and relationships.
    For code analysis, we use it to represent:
    - Nodes: Code entities (functions, classes, modules)
    - Relationships: Connections (calls, imports, inherits)

    This allows us to answer questions like:
    - "What functions call this function?"
    - "What classes inherit from this class?"
    - "What would be affected if I change this?"

NEO4J DATA MODEL:
    ┌─────────────────────────────────────────────────────────────┐
    │                        NODES                                 │
    │  (:Module)    - Python files/modules                         │
    │  (:Class)     - Class definitions                            │
    │  (:Function)  - Functions and methods                        │
    │  (:Variable)  - Variables and constants                      │
    └─────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────┐
    │                     RELATIONSHIPS                            │
    │  -[:CALLS]->      - Function calls another function          │
    │  -[:IMPORTS]->    - Module imports another module            │
    │  -[:INHERITS]->   - Class inherits from another class        │
    │  -[:CONTAINS]->   - Module/Class contains function/method    │
    │  -[:USES]->       - Entity uses another entity               │
    └─────────────────────────────────────────────────────────────┘

HOW IT WORKS:
    1. Entities from parser are stored as nodes
    2. Relationships are stored as edges between nodes
    3. Cypher queries traverse the graph for analysis
    4. Results are returned as entity/relationship objects

CYPHER EXAMPLES:
    Find all callers of a function:
        MATCH (caller:Function)-[:CALLS]->(target:Function {name: $name})
        RETURN caller

    Find inheritance hierarchy:
        MATCH path = (child:Class)-[:INHERITS*]->(parent:Class)
        WHERE child.name = $name
        RETURN path

    Find impact path (up to 3 hops):
        MATCH path = (source)-[*1..3]-(target)
        WHERE source.id = $source_id
        RETURN path

USAGE:
    from src.services.neo4j_service import Neo4jService

    neo4j = Neo4jService()
    await neo4j.connect()

    # Store entities
    await neo4j.store_entities(entities)
    await neo4j.store_relationships(relationships)

    # Query graph
    callers = await neo4j.get_callers(function_id)
    path = await neo4j.find_shortest_path(source_id, target_id)

    await neo4j.close()
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator
from uuid import UUID

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import settings
from src.core.exceptions import Neo4jError
from src.core.logging import LoggerMixin
from src.models.code_entity import CodeEntity, CodeEntityType
from src.models.relationship import Relationship, RelationshipType


class Neo4jService(LoggerMixin):
    """
    Service for managing the Neo4j knowledge graph.

    Handles connection management, entity storage, and graph queries.

    Attributes:
        uri: Neo4j connection URI
        user: Neo4j username
        password: Neo4j password
        driver: Neo4j async driver instance
    """

    def __init__(self) -> None:
        """Initialize the Neo4j service with configuration."""
        self.uri = settings.neo4j_uri
        self.user = settings.neo4j_user
        self.password = settings.neo4j_password
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """
        Establish connection to Neo4j database.

        Creates the async driver and verifies connectivity.

        Raises:
            Neo4jError: If connection fails
        """
        try:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # Verify connection
            await self._driver.verify_connectivity()
            self.logger.info("Connected to Neo4j", uri=self.uri)

            # Create indexes for better performance
            await self._create_indexes()

        except Exception as e:
            self.logger.error("Failed to connect to Neo4j", error=str(e))
            raise Neo4jError(f"Connection failed: {e}")

    async def close(self) -> None:
        """Close the Neo4j connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            self.logger.info("Neo4j connection closed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a Neo4j session context manager.

        Usage:
            async with neo4j.session() as session:
                result = await session.run(query)

        Yields:
            AsyncSession for database operations
        """
        if not self._driver:
            raise Neo4jError("Not connected to Neo4j")

        session = self._driver.session()
        try:
            yield session
        finally:
            await session.close()

    async def _create_indexes(self) -> None:
        """
        Create database indexes for efficient queries.

        Indexes are created on commonly queried properties.
        """
        indexes = [
            "CREATE INDEX entity_id IF NOT EXISTS FOR (e:Entity) ON (e.id)",
            "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.entity_type)",
            "CREATE INDEX entity_file IF NOT EXISTS FOR (e:Entity) ON (e.file_path)",
            "CREATE INDEX function_name IF NOT EXISTS FOR (f:Function) ON (f.name)",
            "CREATE INDEX class_name IF NOT EXISTS FOR (c:Class) ON (c.name)",
            "CREATE INDEX module_name IF NOT EXISTS FOR (m:Module) ON (m.name)",
        ]

        async with self.session() as session:
            for index_query in indexes:
                try:
                    await session.run(index_query)
                except Exception as e:
                    self.logger.warning(
                        "Index creation warning",
                        query=index_query,
                        error=str(e)
                    )

        self.logger.info("Neo4j indexes created/verified")

    # =========================================================================
    # Entity Operations
    # =========================================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def store_entities(
        self,
        entities: list[CodeEntity],
        repository_id: str
    ) -> int:
        """
        Store code entities as nodes in Neo4j.

        Each entity becomes a node with:
        - Labels: Entity, specific type (Function, Class, Module)
        - Properties: All entity attributes

        Args:
            entities: List of code entities to store
            repository_id: ID of the repository these belong to

        Returns:
            Number of entities stored

        Raises:
            Neo4jError: If storage fails
        """
        self.logger.info(
            "Storing entities in Neo4j",
            count=len(entities),
            repository_id=repository_id
        )

        # Batch entities by type for efficient insertion
        batches: dict[str, list[dict[str, Any]]] = {
            "module": [],
            "class": [],
            "function": [],
            "variable": [],
        }

        for entity in entities:
            props = entity.to_neo4j_properties()
            props["repository_id"] = repository_id
            batches[entity.entity_type].append(props)

        stored_count = 0

        async with self.session() as session:
            # Store each type with appropriate labels
            for entity_type, entity_batch in batches.items():
                if not entity_batch:
                    continue

                label = entity_type.capitalize()

                # Use UNWIND for batch insertion
                query = f"""
                UNWIND $entities AS entity
                MERGE (e:Entity:{label} {{id: entity.id}})
                SET e += entity
                """

                try:
                    result = await session.run(query, entities=entity_batch)
                    summary = await result.consume()
                    stored_count += len(entity_batch)

                    self.logger.debug(
                        f"Stored {len(entity_batch)} {label} entities"
                    )

                except Exception as e:
                    self.logger.error(
                        f"Failed to store {label} entities",
                        error=str(e)
                    )
                    raise Neo4jError(f"Entity storage failed: {e}", query=query)

        self.logger.info(f"Stored {stored_count} entities total")
        return stored_count

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def store_relationships(
        self,
        relationships: list[Relationship],
        repository_id: str
    ) -> int:
        """
        Store relationships as edges in Neo4j.

        Each relationship becomes an edge between two nodes.

        Args:
            relationships: List of relationships to store
            repository_id: ID of the repository

        Returns:
            Number of relationships stored

        Raises:
            Neo4jError: If storage fails
        """
        self.logger.info(
            "Storing relationships in Neo4j",
            count=len(relationships),
            repository_id=repository_id
        )

        # Group by relationship type
        batches: dict[str, list[dict[str, Any]]] = {}
        for rel in relationships:
            rel_type = rel.relationship_type
            if rel_type not in batches:
                batches[rel_type] = []
            batches[rel_type].append({
                "id": str(rel.id),
                "source_id": str(rel.source_id),
                "target_id": str(rel.target_id),
                "weight": rel.weight,
                "file_path": rel.file_path or "",
                "line_number": rel.line_number or 0,
                "repository_id": repository_id,
            })

        stored_count = 0

        async with self.session() as session:
            for rel_type, rel_batch in batches.items():
                if not rel_batch:
                    continue

                # Neo4j relationship type (uppercase)
                neo4j_type = rel_type.upper()

                query = f"""
                UNWIND $rels AS rel
                MATCH (source:Entity {{id: rel.source_id}})
                MATCH (target:Entity {{id: rel.target_id}})
                MERGE (source)-[r:{neo4j_type}]->(target)
                SET r.id = rel.id,
                    r.weight = rel.weight,
                    r.file_path = rel.file_path,
                    r.line_number = rel.line_number,
                    r.repository_id = rel.repository_id
                """

                try:
                    result = await session.run(query, rels=rel_batch)
                    await result.consume()
                    stored_count += len(rel_batch)

                    self.logger.debug(
                        f"Stored {len(rel_batch)} {neo4j_type} relationships"
                    )

                except Exception as e:
                    self.logger.error(
                        f"Failed to store {neo4j_type} relationships",
                        error=str(e)
                    )
                    raise Neo4jError(
                        f"Relationship storage failed: {e}",
                        query=query
                    )

        self.logger.info(f"Stored {stored_count} relationships total")
        return stored_count

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def get_entity_by_id(self, entity_id: str) -> dict[str, Any] | None:
        """
        Get a single entity by its ID.

        Args:
            entity_id: UUID of the entity

        Returns:
            Entity properties dict or None if not found
        """
        query = """
        MATCH (e:Entity {id: $entity_id})
        RETURN e
        """

        async with self.session() as session:
            result = await session.run(query, entity_id=entity_id)
            record = await result.single()
            if record:
                return dict(record["e"])
        return None

    async def get_entity_by_name(
        self,
        name: str,
        repository_id: str,
        file_path: str | None = None
    ) -> dict[str, Any] | None:
        """
        Get an entity by name within a repository.

        Args:
            name: Entity name
            repository_id: Repository UUID
            file_path: Optional file path to narrow search

        Returns:
            Entity properties dict or None if not found
        """
        if file_path:
            query = """
            MATCH (e:Entity {name: $name, repository_id: $repo_id, file_path: $file_path})
            RETURN e
            LIMIT 1
            """
            params = {
                "name": name,
                "repo_id": repository_id,
                "file_path": file_path
            }
        else:
            query = """
            MATCH (e:Entity {name: $name, repository_id: $repo_id})
            RETURN e
            LIMIT 1
            """
            params = {"name": name, "repo_id": repository_id}

        async with self.session() as session:
            result = await session.run(query, **params)
            record = await result.single()
            if record:
                return dict(record["e"])
        return None

    async def get_callers(
        self,
        entity_id: str,
        max_depth: int = 1
    ) -> list[dict[str, Any]]:
        """
        Get all entities that call the specified entity.

        Args:
            entity_id: UUID of the target entity
            max_depth: Maximum call chain depth

        Returns:
            List of calling entity dicts
        """
        query = """
        MATCH (caller:Entity)-[:CALLS*1..$depth]->(target:Entity {id: $entity_id})
        RETURN DISTINCT caller,
               length(shortestPath((caller)-[:CALLS*]->(target))) as distance
        ORDER BY distance
        """

        async with self.session() as session:
            result = await session.run(
                query,
                entity_id=entity_id,
                depth=max_depth
            )
            records = await result.values()
            return [{"entity": dict(r[0]), "distance": r[1]} for r in records]

    async def get_callees(
        self,
        entity_id: str,
        max_depth: int = 1
    ) -> list[dict[str, Any]]:
        """
        Get all entities called by the specified entity.

        Args:
            entity_id: UUID of the source entity
            max_depth: Maximum call chain depth

        Returns:
            List of called entity dicts
        """
        query = """
        MATCH (source:Entity {id: $entity_id})-[:CALLS*1..$depth]->(callee:Entity)
        RETURN DISTINCT callee,
               length(shortestPath((source)-[:CALLS*]->(callee))) as distance
        ORDER BY distance
        """

        async with self.session() as session:
            result = await session.run(
                query,
                entity_id=entity_id,
                depth=max_depth
            )
            records = await result.values()
            return [{"entity": dict(r[0]), "distance": r[1]} for r in records]

    async def get_dependencies(
        self,
        entity_id: str,
        max_depth: int = 2
    ) -> list[dict[str, Any]]:
        """
        Get all entities that the specified entity depends on.

        Follows CALLS, USES, and IMPORTS relationships.

        Args:
            entity_id: UUID of the source entity
            max_depth: Maximum traversal depth

        Returns:
            List of dependency entity dicts with relationship info
        """
        query = """
        MATCH path = (source:Entity {id: $entity_id})-[:CALLS|USES|IMPORTS*1..$depth]->(dep:Entity)
        WITH dep, path, length(path) as distance
        RETURN DISTINCT dep, distance,
               [r in relationships(path) | type(r)] as rel_types
        ORDER BY distance
        """

        async with self.session() as session:
            result = await session.run(
                query,
                entity_id=entity_id,
                depth=max_depth
            )
            records = await result.values()
            return [
                {
                    "entity": dict(r[0]),
                    "distance": r[1],
                    "relationship_path": r[2]
                }
                for r in records
            ]

    async def get_dependents(
        self,
        entity_id: str,
        max_depth: int = 3
    ) -> list[dict[str, Any]]:
        """
        Get all entities that depend on the specified entity.

        This is critical for impact analysis - finds everything
        that might be affected by changes.

        Args:
            entity_id: UUID of the target entity
            max_depth: Maximum traversal depth

        Returns:
            List of dependent entity dicts with path info
        """
        query = """
        MATCH path = (dependent:Entity)-[:CALLS|USES|IMPORTS|INHERITS*1..$depth]->(target:Entity {id: $entity_id})
        WITH dependent, path, length(path) as distance
        RETURN DISTINCT dependent, distance,
               [r in relationships(path) | type(r)] as rel_types,
               [n in nodes(path) | n.name] as path_names
        ORDER BY distance
        """

        async with self.session() as session:
            result = await session.run(
                query,
                entity_id=entity_id,
                depth=max_depth
            )
            records = await result.values()
            return [
                {
                    "entity": dict(r[0]),
                    "distance": r[1],
                    "relationship_path": r[2],
                    "path_names": r[3]
                }
                for r in records
            ]

    async def find_shortest_path(
        self,
        source_id: str,
        target_id: str
    ) -> list[dict[str, Any]] | None:
        """
        Find the shortest path between two entities.

        Args:
            source_id: UUID of source entity
            target_id: UUID of target entity

        Returns:
            List of nodes and relationships in the path, or None
        """
        query = """
        MATCH path = shortestPath(
            (source:Entity {id: $source_id})-[*]-(target:Entity {id: $target_id})
        )
        RETURN [n in nodes(path) | {id: n.id, name: n.name, type: n.entity_type}] as nodes,
               [r in relationships(path) | type(r)] as relationships
        """

        async with self.session() as session:
            result = await session.run(
                query,
                source_id=source_id,
                target_id=target_id
            )
            record = await result.single()
            if record:
                return {
                    "nodes": record["nodes"],
                    "relationships": record["relationships"]
                }
        return None

    async def get_class_hierarchy(
        self,
        class_id: str
    ) -> dict[str, Any]:
        """
        Get the full inheritance hierarchy for a class.

        Args:
            class_id: UUID of the class

        Returns:
            Dict with ancestors and descendants
        """
        # Get ancestors (what this class inherits from)
        ancestors_query = """
        MATCH path = (child:Class {id: $class_id})-[:INHERITS*]->(parent:Class)
        RETURN parent, length(path) as depth
        ORDER BY depth
        """

        # Get descendants (what inherits from this class)
        descendants_query = """
        MATCH path = (child:Class)-[:INHERITS*]->(parent:Class {id: $class_id})
        RETURN child, length(path) as depth
        ORDER BY depth
        """

        async with self.session() as session:
            ancestors_result = await session.run(ancestors_query, class_id=class_id)
            ancestors = [
                {"entity": dict(r[0]), "depth": r[1]}
                for r in await ancestors_result.values()
            ]

            descendants_result = await session.run(descendants_query, class_id=class_id)
            descendants = [
                {"entity": dict(r[0]), "depth": r[1]}
                for r in await descendants_result.values()
            ]

        return {
            "ancestors": ancestors,
            "descendants": descendants
        }

    async def get_repository_stats(
        self,
        repository_id: str
    ) -> dict[str, Any]:
        """
        Get statistics for a repository.

        Args:
            repository_id: UUID of the repository

        Returns:
            Dict with entity and relationship counts
        """
        query = """
        MATCH (e:Entity {repository_id: $repo_id})
        WITH count(e) as total_entities,
             count(CASE WHEN e.entity_type = 'function' THEN 1 END) as functions,
             count(CASE WHEN e.entity_type = 'class' THEN 1 END) as classes,
             count(CASE WHEN e.entity_type = 'module' THEN 1 END) as modules
        RETURN total_entities, functions, classes, modules
        """

        rel_query = """
        MATCH (e:Entity {repository_id: $repo_id})-[r]-()
        RETURN type(r) as rel_type, count(r) as count
        """

        async with self.session() as session:
            result = await session.run(query, repo_id=repository_id)
            record = await result.single()

            rel_result = await session.run(rel_query, repo_id=repository_id)
            rel_counts = {
                r["rel_type"]: r["count"]
                for r in await rel_result.values()
            }

            return {
                "total_entities": record["total_entities"] if record else 0,
                "functions": record["functions"] if record else 0,
                "classes": record["classes"] if record else 0,
                "modules": record["modules"] if record else 0,
                "relationships": rel_counts
            }

    async def delete_repository(self, repository_id: str) -> int:
        """
        Delete all data for a repository.

        Args:
            repository_id: UUID of the repository

        Returns:
            Number of nodes deleted
        """
        query = """
        MATCH (e:Entity {repository_id: $repo_id})
        DETACH DELETE e
        RETURN count(e) as deleted
        """

        async with self.session() as session:
            result = await session.run(query, repo_id=repository_id)
            record = await result.single()
            deleted = record["deleted"] if record else 0

        self.logger.info(
            "Deleted repository data",
            repository_id=repository_id,
            nodes_deleted=deleted
        )
        return deleted

    async def health_check(self) -> bool:
        """
        Check if Neo4j is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            async with self.session() as session:
                result = await session.run("RETURN 1 as n")
                record = await result.single()
                return record["n"] == 1
        except Exception as e:
            self.logger.error("Neo4j health check failed", error=str(e))
            return False
