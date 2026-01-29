"""
Context Aggregator
==================

Aggregates and prioritizes context from multiple sources for LLM prompts:
- Vector DB (semantic similarity)
- Knowledge Graph (structural relationships)
- Conversation History
- User Preferences

WHY CONTEXT AGGREGATION?
    LLMs perform better with relevant context, but context windows are limited.
    The aggregator:
    1. Gathers context from multiple sources
    2. Ranks and prioritizes by relevance
    3. Fits within token limits
    4. Formats for optimal LLM understanding

ARCHITECTURE:
    ┌─────────────────────────────────────────────────────────────────┐
    │                    CONTEXT SOURCES                               │
    │                                                                  │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
    │  │ Vector   │  │  Neo4j   │  │ History  │  │  User    │       │
    │  │   DB     │  │  Graph   │  │ (Cosmos) │  │  Prefs   │       │
    │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
    │       │             │             │             │              │
    └───────┼─────────────┼─────────────┼─────────────┼──────────────┘
            │             │             │             │
            ▼             ▼             ▼             ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                  CONTEXT AGGREGATOR                              │
    │                                                                  │
    │  1. COLLECT   - Gather from all sources in parallel             │
    │  2. SCORE     - Calculate relevance scores                      │
    │  3. DEDUPE    - Remove duplicates                               │
    │  4. RANK      - Sort by priority                                │
    │  5. TRUNCATE  - Fit within token budget                         │
    │  6. FORMAT    - Structure for LLM                               │
    │                                                                  │
    └─────────────────────────────────────────────────────────────────┘
            │
            ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                  AGGREGATED CONTEXT                              │
    │                                                                  │
    │  {                                                              │
    │    "similar_code": [...],      # From Vector DB                 │
    │    "related_entities": [...],  # From Neo4j                     │
    │    "conversation": [...],      # From History                   │
    │    "metadata": {...}           # Aggregation info               │
    │  }                                                              │
    └─────────────────────────────────────────────────────────────────┘

SCORING ALGORITHM:
    Each context item receives a composite score:

    score = (
        semantic_similarity * 0.4 +    # How semantically similar
        structural_relevance * 0.3 +   # How structurally related
        recency * 0.2 +                # How recent (conversations)
        source_priority * 0.1          # Source-specific weight
    )

TOKEN BUDGETING:
    Total budget is divided among context types:

    ┌─────────────────────────────────────┐
    │       TOKEN BUDGET (4000)           │
    ├─────────────────────────────────────┤
    │ Similar Code:     40% (1600)        │
    │ Related Entities: 30% (1200)        │
    │ Conversation:     20% (800)         │
    │ System/Reserved:  10% (400)         │
    └─────────────────────────────────────┘

USAGE:
    from src.services.context_aggregator import ContextAggregator

    aggregator = ContextAggregator(
        vector_service=vector,
        neo4j_service=neo4j,
        token_budget=4000
    )

    context = await aggregator.aggregate(
        query="How do I validate emails?",
        repository_id="repo-123",
        conversation_history=[...],
        context_config=ContextConfig(
            include_similar_code=True,
            include_relationships=True,
            max_code_examples=5
        )
    )
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.logging import LoggerMixin
from src.services.neo4j_service import Neo4jService
from src.services.vector_service import VectorService


class ContextSource(Enum):
    """Source of context."""
    VECTOR_DB = "vector_db"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    CONVERSATION = "conversation"
    USER_CONTEXT = "user_context"


class ContextPriority(Enum):
    """Priority level for context."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class ContextItem:
    """
    A single item of context.

    Attributes:
        content: The actual content
        source: Where it came from
        score: Relevance score (0-1)
        priority: Priority level
        token_estimate: Estimated token count
        metadata: Additional information
    """
    content: str
    source: ContextSource
    score: float
    priority: ContextPriority = ContextPriority.MEDIUM
    token_estimate: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Estimate tokens if not provided."""
        if self.token_estimate == 0:
            # Rough estimate: ~4 characters per token
            self.token_estimate = len(self.content) // 4


@dataclass
class ContextConfig:
    """
    Configuration for context aggregation.

    Attributes:
        include_similar_code: Include semantically similar code
        include_relationships: Include graph relationships
        include_conversation: Include conversation history
        max_code_examples: Maximum code examples to include
        max_relationships: Maximum relationships to include
        max_conversation_turns: Maximum conversation turns
        similarity_threshold: Minimum similarity score
    """
    include_similar_code: bool = True
    include_relationships: bool = True
    include_conversation: bool = True

    max_code_examples: int = 5
    max_relationships: int = 10
    max_conversation_turns: int = 10

    similarity_threshold: float = 0.3
    relationship_depth: int = 2

    # Token budget allocation (percentages)
    code_budget_pct: float = 0.40
    relationship_budget_pct: float = 0.30
    conversation_budget_pct: float = 0.20
    reserved_budget_pct: float = 0.10


@dataclass
class AggregatedContext:
    """
    The final aggregated context.

    Attributes:
        similar_code: Code examples from vector DB
        related_entities: Entities from knowledge graph
        conversation_context: Relevant conversation history
        formatted_context: Pre-formatted string for LLM
        total_tokens: Total estimated tokens
        metadata: Aggregation metadata
    """
    similar_code: list[ContextItem] = field(default_factory=list)
    related_entities: list[ContextItem] = field(default_factory=list)
    conversation_context: list[ContextItem] = field(default_factory=list)
    formatted_context: str = ""
    total_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "similar_code": [
                {"content": item.content, "score": item.score, "metadata": item.metadata}
                for item in self.similar_code
            ],
            "related_entities": [
                {"content": item.content, "score": item.score, "metadata": item.metadata}
                for item in self.related_entities
            ],
            "conversation_context": [
                {"content": item.content, "metadata": item.metadata}
                for item in self.conversation_context
            ],
            "formatted_context": self.formatted_context,
            "total_tokens": self.total_tokens,
            "metadata": self.metadata
        }


class ContextAggregator(LoggerMixin):
    """
    Aggregates context from multiple sources for LLM prompts.

    This class is responsible for:
    1. Gathering relevant context from various sources
    2. Scoring and ranking by relevance
    3. Fitting within token budgets
    4. Formatting for LLM consumption

    Attributes:
        vector: Vector service for semantic search
        neo4j: Neo4j service for graph queries
        token_budget: Maximum tokens for context
    """

    def __init__(
        self,
        vector_service: VectorService,
        neo4j_service: Neo4jService,
        token_budget: int = 4000
    ) -> None:
        """
        Initialize the context aggregator.

        Args:
            vector_service: Vector DB service
            neo4j_service: Neo4j graph service
            token_budget: Maximum tokens for context
        """
        self.vector = vector_service
        self.neo4j = neo4j_service
        self.token_budget = token_budget

    async def aggregate(
        self,
        query: str,
        repository_id: str | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        context_entities: list[str] | None = None,
        config: ContextConfig | None = None
    ) -> AggregatedContext:
        """
        Aggregate context from all sources.

        This is the main entry point. It:
        1. Collects context from all enabled sources in parallel
        2. Scores and ranks all items
        3. Selects items within token budget
        4. Formats for LLM

        Args:
            query: User query to find relevant context for
            repository_id: Repository to search in
            conversation_history: Previous conversation messages
            context_entities: Specific entity names to include
            config: Aggregation configuration

        Returns:
            AggregatedContext with all relevant context

        Example:
            context = await aggregator.aggregate(
                query="How do I add authentication?",
                repository_id="repo-123",
                conversation_history=[
                    {"role": "user", "content": "Previous question"},
                    {"role": "assistant", "content": "Previous answer"}
                ]
            )
        """
        config = config or ContextConfig()

        self.logger.info(
            "Aggregating context",
            query_preview=query[:50],
            repository_id=repository_id
        )

        # Calculate token budgets for each source
        budgets = self._calculate_budgets(config)

        # Collect context from all sources in parallel
        tasks = []

        if config.include_similar_code and repository_id:
            tasks.append(self._get_similar_code(
                query, repository_id, config, budgets["code"]
            ))
        else:
            tasks.append(asyncio.coroutine(lambda: [])())

        if config.include_relationships and repository_id:
            tasks.append(self._get_related_entities(
                query, repository_id, context_entities, config, budgets["relationships"]
            ))
        else:
            tasks.append(asyncio.coroutine(lambda: [])())

        if config.include_conversation and conversation_history:
            tasks.append(asyncio.coroutine(lambda: self._process_conversation(
                conversation_history, config, budgets["conversation"]
            ))())
        else:
            tasks.append(asyncio.coroutine(lambda: [])())

        # Wait for all sources
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any errors
        similar_code = results[0] if not isinstance(results[0], Exception) else []
        related_entities = results[1] if not isinstance(results[1], Exception) else []
        conversation_items = results[2] if not isinstance(results[2], Exception) else []

        if isinstance(results[0], Exception):
            self.logger.warning(f"Similar code search failed: {results[0]}")
        if isinstance(results[1], Exception):
            self.logger.warning(f"Related entities search failed: {results[1]}")

        # Build aggregated context
        context = AggregatedContext(
            similar_code=similar_code,
            related_entities=related_entities,
            conversation_context=conversation_items,
            metadata={
                "query": query,
                "repository_id": repository_id,
                "sources_used": {
                    "vector_db": len(similar_code) > 0,
                    "knowledge_graph": len(related_entities) > 0,
                    "conversation": len(conversation_items) > 0
                },
                "config": {
                    "max_code_examples": config.max_code_examples,
                    "max_relationships": config.max_relationships,
                    "similarity_threshold": config.similarity_threshold
                }
            }
        )

        # Format the context
        context.formatted_context = self._format_context(context)
        context.total_tokens = self._estimate_tokens(context.formatted_context)

        self.logger.info(
            "Context aggregation complete",
            code_items=len(similar_code),
            entity_items=len(related_entities),
            total_tokens=context.total_tokens
        )

        return context

    def _calculate_budgets(self, config: ContextConfig) -> dict[str, int]:
        """
        Calculate token budgets for each source.

        Args:
            config: Context configuration

        Returns:
            Dict with budget for each source type
        """
        return {
            "code": int(self.token_budget * config.code_budget_pct),
            "relationships": int(self.token_budget * config.relationship_budget_pct),
            "conversation": int(self.token_budget * config.conversation_budget_pct),
            "reserved": int(self.token_budget * config.reserved_budget_pct)
        }

    async def _get_similar_code(
        self,
        query: str,
        repository_id: str,
        config: ContextConfig,
        budget: int
    ) -> list[ContextItem]:
        """
        Get similar code from vector DB.

        Args:
            query: Search query
            repository_id: Repository ID
            config: Configuration
            budget: Token budget

        Returns:
            List of context items
        """
        try:
            results = await self.vector.search(
                query=query,
                repository_id=repository_id,
                limit=config.max_code_examples * 2,  # Get extra for filtering
                entity_types=["function", "class", "method"]
            )

            items = []
            current_tokens = 0

            for result in results:
                # Skip if below threshold
                score = result.get("score", 0)
                if score < config.similarity_threshold:
                    continue

                content = result.get("document", "")
                metadata = result.get("metadata", {})

                item = ContextItem(
                    content=content,
                    source=ContextSource.VECTOR_DB,
                    score=score,
                    priority=self._score_to_priority(score),
                    metadata={
                        "entity_id": result.get("entity_id"),
                        "name": metadata.get("name", ""),
                        "file_path": metadata.get("file_path", ""),
                        "entity_type": metadata.get("entity_type", "")
                    }
                )

                # Check if we're within budget
                if current_tokens + item.token_estimate > budget:
                    break

                items.append(item)
                current_tokens += item.token_estimate

                if len(items) >= config.max_code_examples:
                    break

            return items

        except Exception as e:
            self.logger.error(f"Similar code retrieval failed: {e}")
            return []

    async def _get_related_entities(
        self,
        query: str,
        repository_id: str,
        context_entities: list[str] | None,
        config: ContextConfig,
        budget: int
    ) -> list[ContextItem]:
        """
        Get related entities from knowledge graph.

        Args:
            query: Search query
            repository_id: Repository ID
            context_entities: Specific entities to include
            config: Configuration
            budget: Token budget

        Returns:
            List of context items
        """
        items = []
        current_tokens = 0

        try:
            # If specific entities are requested, get them and their relationships
            if context_entities:
                for entity_name in context_entities:
                    entity = await self.neo4j.get_entity_by_name(
                        entity_name, repository_id
                    )
                    if entity:
                        content = self._format_entity(entity)
                        item = ContextItem(
                            content=content,
                            source=ContextSource.KNOWLEDGE_GRAPH,
                            score=1.0,  # Explicitly requested
                            priority=ContextPriority.HIGH,
                            metadata={
                                "entity_id": entity.get("id"),
                                "name": entity.get("name"),
                                "entity_type": entity.get("entity_type"),
                                "relationship": "requested"
                            }
                        )

                        if current_tokens + item.token_estimate <= budget:
                            items.append(item)
                            current_tokens += item.token_estimate

                        # Also get related entities
                        related = await self.neo4j.get_dependencies(
                            entity.get("id"),
                            max_depth=config.relationship_depth
                        )

                        for rel in related[:config.max_relationships]:
                            rel_entity = rel.get("entity", {})
                            content = self._format_entity(rel_entity)
                            rel_item = ContextItem(
                                content=content,
                                source=ContextSource.KNOWLEDGE_GRAPH,
                                score=0.7,
                                priority=ContextPriority.MEDIUM,
                                metadata={
                                    "entity_id": rel_entity.get("id"),
                                    "name": rel_entity.get("name"),
                                    "entity_type": rel_entity.get("entity_type"),
                                    "relationship": rel.get("relationship_type", "related")
                                }
                            )

                            if current_tokens + rel_item.token_estimate <= budget:
                                items.append(rel_item)
                                current_tokens += rel_item.token_estimate

            return items

        except Exception as e:
            self.logger.error(f"Related entities retrieval failed: {e}")
            return []

    def _process_conversation(
        self,
        history: list[dict[str, Any]],
        config: ContextConfig,
        budget: int
    ) -> list[ContextItem]:
        """
        Process conversation history into context items.

        Args:
            history: Conversation messages
            config: Configuration
            budget: Token budget

        Returns:
            List of context items
        """
        items = []
        current_tokens = 0

        # Get recent messages (most recent first)
        recent = history[-config.max_conversation_turns:]

        for i, msg in enumerate(recent):
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Calculate recency score (more recent = higher)
            recency_score = (i + 1) / len(recent)

            item = ContextItem(
                content=f"{role}: {content}",
                source=ContextSource.CONVERSATION,
                score=recency_score,
                priority=ContextPriority.MEDIUM,
                metadata={
                    "role": role,
                    "turn": i
                }
            )

            if current_tokens + item.token_estimate <= budget:
                items.append(item)
                current_tokens += item.token_estimate

        return items

    def _format_entity(self, entity: dict[str, Any]) -> str:
        """
        Format an entity for inclusion in context.

        Args:
            entity: Entity data

        Returns:
            Formatted string
        """
        name = entity.get("name", "Unknown")
        entity_type = entity.get("entity_type", "unknown")
        file_path = entity.get("file_path", "")
        docstring = entity.get("docstring", "")
        source = entity.get("source_code", "")

        parts = [f"### {entity_type.title()}: {name}"]

        if file_path:
            parts.append(f"File: {file_path}")

        if docstring:
            parts.append(f"Description: {docstring}")

        if source:
            # Limit source code length
            source_preview = source[:500] + "..." if len(source) > 500 else source
            parts.append(f"```\n{source_preview}\n```")

        return "\n".join(parts)

    def _format_context(self, context: AggregatedContext) -> str:
        """
        Format the aggregated context into a string for LLM.

        Args:
            context: Aggregated context

        Returns:
            Formatted context string
        """
        sections = []

        # Similar code section
        if context.similar_code:
            code_section = "## Similar Code Examples\n\n"
            for item in context.similar_code:
                name = item.metadata.get("name", "Example")
                score = item.score
                code_section += f"### {name} (similarity: {score:.2f})\n"
                code_section += f"{item.content}\n\n"
            sections.append(code_section)

        # Related entities section
        if context.related_entities:
            entity_section = "## Related Code Entities\n\n"
            for item in context.related_entities:
                entity_section += f"{item.content}\n\n"
            sections.append(entity_section)

        # Conversation section
        if context.conversation_context:
            conv_section = "## Recent Conversation\n\n"
            for item in context.conversation_context:
                conv_section += f"{item.content}\n\n"
            sections.append(conv_section)

        return "\n".join(sections) if sections else "No specific context available."

    def _score_to_priority(self, score: float) -> ContextPriority:
        """
        Convert a numeric score to priority level.

        Args:
            score: Score (0-1)

        Returns:
            Priority level
        """
        if score >= 0.9:
            return ContextPriority.CRITICAL
        elif score >= 0.7:
            return ContextPriority.HIGH
        elif score >= 0.5:
            return ContextPriority.MEDIUM
        else:
            return ContextPriority.LOW

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        # Rough estimate: ~4 characters per token for English
        return len(text) // 4

    async def aggregate_for_generation(
        self,
        prompt: str,
        repository_id: str,
        context_entities: list[str] | None = None
    ) -> AggregatedContext:
        """
        Aggregate context specifically for code generation.

        Optimized for code generation use case with emphasis on similar code.

        Args:
            prompt: Generation prompt
            repository_id: Repository ID
            context_entities: Specific entities to include

        Returns:
            Aggregated context optimized for generation
        """
        config = ContextConfig(
            include_similar_code=True,
            include_relationships=True,
            include_conversation=False,  # Not relevant for generation
            max_code_examples=7,
            max_relationships=5,
            similarity_threshold=0.25,
            code_budget_pct=0.60,  # More budget for code
            relationship_budget_pct=0.35,
            conversation_budget_pct=0.0,
            reserved_budget_pct=0.05
        )

        return await self.aggregate(
            query=prompt,
            repository_id=repository_id,
            context_entities=context_entities,
            config=config
        )

    async def aggregate_for_chat(
        self,
        query: str,
        repository_id: str | None,
        conversation_history: list[dict[str, Any]] | None
    ) -> AggregatedContext:
        """
        Aggregate context specifically for chat.

        Optimized for chat use case with conversation context.

        Args:
            query: User query
            repository_id: Repository ID (optional)
            conversation_history: Conversation history

        Returns:
            Aggregated context optimized for chat
        """
        config = ContextConfig(
            include_similar_code=repository_id is not None,
            include_relationships=repository_id is not None,
            include_conversation=conversation_history is not None,
            max_code_examples=3,
            max_relationships=5,
            max_conversation_turns=8,
            similarity_threshold=0.35,
            code_budget_pct=0.30,
            relationship_budget_pct=0.25,
            conversation_budget_pct=0.35,
            reserved_budget_pct=0.10
        )

        return await self.aggregate(
            query=query,
            repository_id=repository_id,
            conversation_history=conversation_history,
            config=config
        )
