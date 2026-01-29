"""
Cosmos DB Service
=================

Manages conversation storage in Azure Cosmos DB.
Provides persistence for chat conversations and message history.

WHAT IS COSMOS DB?
    Azure Cosmos DB is a globally distributed, multi-model database.
    We use it because:
    - Low latency reads/writes
    - Automatic scaling
    - Built-in partitioning
    - JSON document storage (perfect for conversations)

DATA MODEL:
    Database: code_intel
    Container: conversations
    Partition Key: /user_id

    This means:
    - All conversations for a user are in the same partition
    - Fast queries for a user's conversations
    - Scalable across users

COSMOS DB DOCUMENT STRUCTURE:
    {
        "id": "conversation-uuid",          // Required - unique ID
        "user_id": "user-123",              // Partition key
        "repository_id": "repo-uuid",
        "title": "Discuss validation",
        "messages": [
            {
                "id": "message-uuid",
                "role": "user",
                "content": "How do I validate?",
                "created_at": "2024-01-29T10:30:00Z"
            },
            ...
        ],
        "created_at": "2024-01-29T10:30:00Z",
        "updated_at": "2024-01-29T10:45:00Z"
    }

HOW IT WORKS:
    1. User sends message → Add to conversation
    2. Conversation saved to Cosmos DB
    3. User returns → Load conversation history
    4. AI has full context from history

USAGE:
    from src.services.cosmos_service import CosmosService

    cosmos = CosmosService()
    await cosmos.initialize()

    # Create conversation
    conv = await cosmos.create_conversation(user_id, repo_id)

    # Add message
    await cosmos.add_message(conv.id, user_id, message)

    # Get conversation
    conv = await cosmos.get_conversation(conv_id, user_id)

    # List user's conversations
    convs = await cosmos.list_conversations(user_id)
"""

import asyncio
from typing import Any
from uuid import UUID

from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import settings
from src.core.exceptions import StorageError
from src.core.logging import LoggerMixin
from src.models.conversation import (
    Conversation,
    ConversationSummary,
    Message,
    MessageRole,
    MessageType,
)


class CosmosDBError(StorageError):
    """Raised when Cosmos DB operations fail."""

    def __init__(self, message: str, operation: str | None = None) -> None:
        details = {}
        if operation:
            details["operation"] = operation
        super().__init__(
            message=f"Cosmos DB error: {message}",
            code="COSMOS_DB_ERROR",
            details=details
        )


class CosmosService(LoggerMixin):
    """
    Service for managing conversations in Azure Cosmos DB.

    Handles CRUD operations for conversations and messages.

    Attributes:
        endpoint: Cosmos DB endpoint URL
        key: Cosmos DB access key
        database_name: Name of the database
        container_name: Name of the conversations container
    """

    def __init__(self) -> None:
        """Initialize the Cosmos DB service with configuration."""
        self.endpoint = settings.cosmos_endpoint
        self.key = settings.cosmos_key
        self.database_name = settings.cosmos_database
        self.container_name = settings.cosmos_container

        self._client: CosmosClient | None = None
        self._database = None
        self._container = None

    async def initialize(self) -> None:
        """
        Initialize Cosmos DB client and ensure database/container exist.

        Creates the database and container if they don't exist.

        Raises:
            CosmosDBError: If initialization fails
        """
        try:
            self.logger.info(
                "Initializing Cosmos DB",
                endpoint=self.endpoint,
                database=self.database_name
            )

            # Create client
            self._client = CosmosClient(self.endpoint, self.key)

            # Create database if not exists
            self._database = await self._client.create_database_if_not_exists(
                id=self.database_name
            )

            # Create container if not exists
            # Partition key is user_id for efficient user-scoped queries
            self._container = await self._database.create_container_if_not_exists(
                id=self.container_name,
                partition_key=PartitionKey(path="/user_id"),
                offer_throughput=400  # Minimum RU/s
            )

            self.logger.info("Cosmos DB initialized successfully")

        except Exception as e:
            self.logger.error("Failed to initialize Cosmos DB", error=str(e))
            raise CosmosDBError(f"Initialization failed: {e}", operation="initialize")

    async def close(self) -> None:
        """Close the Cosmos DB client connection."""
        if self._client:
            await self._client.close()
            self._client = None
            self.logger.info("Cosmos DB connection closed")

    @property
    def container(self):
        """Get the container, raising if not initialized."""
        if not self._container:
            raise CosmosDBError("Cosmos DB not initialized", operation="get_container")
        return self._container

    # =========================================================================
    # Conversation Operations
    # =========================================================================

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def create_conversation(
        self,
        user_id: str,
        repository_id: str | None = None,
        title: str = "New Conversation"
    ) -> Conversation:
        """
        Create a new conversation.

        Args:
            user_id: ID of the user
            repository_id: Optional repository being discussed
            title: Conversation title

        Returns:
            Created Conversation object

        Raises:
            CosmosDBError: If creation fails
        """
        self.logger.info(
            "Creating conversation",
            user_id=user_id,
            repository_id=repository_id
        )

        conversation = Conversation(
            user_id=user_id,
            repository_id=repository_id,
            title=title
        )

        try:
            await self.container.create_item(
                body=conversation.to_cosmos_document()
            )

            self.logger.info(
                "Conversation created",
                conversation_id=str(conversation.id)
            )

            return conversation

        except Exception as e:
            self.logger.error("Failed to create conversation", error=str(e))
            raise CosmosDBError(f"Create failed: {e}", operation="create_conversation")

    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> Conversation | None:
        """
        Get a conversation by ID.

        Args:
            conversation_id: UUID of the conversation
            user_id: User ID (partition key)

        Returns:
            Conversation or None if not found
        """
        try:
            response = await self.container.read_item(
                item=conversation_id,
                partition_key=user_id
            )
            return Conversation.from_cosmos_document(response)

        except CosmosResourceNotFoundError:
            return None

        except Exception as e:
            self.logger.error(
                "Failed to get conversation",
                conversation_id=conversation_id,
                error=str(e)
            )
            raise CosmosDBError(f"Get failed: {e}", operation="get_conversation")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def update_conversation(
        self,
        conversation: Conversation
    ) -> Conversation:
        """
        Update an existing conversation.

        Args:
            conversation: Conversation to update

        Returns:
            Updated Conversation

        Raises:
            CosmosDBError: If update fails
        """
        try:
            await self.container.replace_item(
                item=str(conversation.id),
                body=conversation.to_cosmos_document()
            )

            return conversation

        except Exception as e:
            self.logger.error(
                "Failed to update conversation",
                conversation_id=str(conversation.id),
                error=str(e)
            )
            raise CosmosDBError(f"Update failed: {e}", operation="update_conversation")

    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: UUID of the conversation
            user_id: User ID (partition key)

        Returns:
            True if deleted, False if not found
        """
        try:
            await self.container.delete_item(
                item=conversation_id,
                partition_key=user_id
            )

            self.logger.info(
                "Conversation deleted",
                conversation_id=conversation_id
            )
            return True

        except CosmosResourceNotFoundError:
            return False

        except Exception as e:
            self.logger.error(
                "Failed to delete conversation",
                conversation_id=conversation_id,
                error=str(e)
            )
            raise CosmosDBError(f"Delete failed: {e}", operation="delete_conversation")

    # =========================================================================
    # Message Operations
    # =========================================================================

    async def add_message(
        self,
        conversation_id: str,
        user_id: str,
        message: Message
    ) -> Conversation:
        """
        Add a message to a conversation.

        Args:
            conversation_id: UUID of the conversation
            user_id: User ID (partition key)
            message: Message to add

        Returns:
            Updated Conversation

        Raises:
            CosmosDBError: If operation fails
        """
        # Get existing conversation
        conversation = await self.get_conversation(conversation_id, user_id)

        if not conversation:
            raise CosmosDBError(
                f"Conversation not found: {conversation_id}",
                operation="add_message"
            )

        # Add message
        conversation.add_message(message)

        # Save updated conversation
        return await self.update_conversation(conversation)

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def list_conversations(
        self,
        user_id: str,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> list[ConversationSummary]:
        """
        List conversations for a user.

        Args:
            user_id: User ID
            include_archived: Include archived conversations
            limit: Maximum results
            offset: Skip first N results

        Returns:
            List of conversation summaries
        """
        try:
            # Build query
            query = "SELECT * FROM c WHERE c.user_id = @user_id"
            parameters = [{"name": "@user_id", "value": user_id}]

            if not include_archived:
                query += " AND (c.is_archived = false OR NOT IS_DEFINED(c.is_archived))"

            query += " ORDER BY c.updated_at DESC"
            query += f" OFFSET {offset} LIMIT {limit}"

            # Execute query
            items = self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=user_id
            )

            # Convert to summaries
            summaries = []
            async for item in items:
                conv = Conversation.from_cosmos_document(item)
                summaries.append(ConversationSummary.from_conversation(conv))

            return summaries

        except Exception as e:
            self.logger.error(
                "Failed to list conversations",
                user_id=user_id,
                error=str(e)
            )
            raise CosmosDBError(f"List failed: {e}", operation="list_conversations")

    async def search_conversations(
        self,
        user_id: str,
        search_text: str,
        limit: int = 20
    ) -> list[ConversationSummary]:
        """
        Search conversations by title or content.

        Args:
            user_id: User ID
            search_text: Text to search for
            limit: Maximum results

        Returns:
            List of matching conversation summaries
        """
        try:
            # Search in title (Cosmos DB doesn't support full-text search,
            # so this is a simple CONTAINS query)
            query = """
            SELECT * FROM c
            WHERE c.user_id = @user_id
            AND CONTAINS(LOWER(c.title), LOWER(@search))
            ORDER BY c.updated_at DESC
            """

            items = self.container.query_items(
                query=query,
                parameters=[
                    {"name": "@user_id", "value": user_id},
                    {"name": "@search", "value": search_text}
                ],
                partition_key=user_id,
                max_item_count=limit
            )

            summaries = []
            async for item in items:
                conv = Conversation.from_cosmos_document(item)
                summaries.append(ConversationSummary.from_conversation(conv))

            return summaries

        except Exception as e:
            self.logger.error(
                "Failed to search conversations",
                error=str(e)
            )
            raise CosmosDBError(f"Search failed: {e}", operation="search_conversations")

    async def get_conversations_by_repository(
        self,
        user_id: str,
        repository_id: str,
        limit: int = 20
    ) -> list[ConversationSummary]:
        """
        Get conversations about a specific repository.

        Args:
            user_id: User ID
            repository_id: Repository ID
            limit: Maximum results

        Returns:
            List of conversation summaries
        """
        try:
            query = """
            SELECT * FROM c
            WHERE c.user_id = @user_id
            AND c.repository_id = @repo_id
            ORDER BY c.updated_at DESC
            """

            items = self.container.query_items(
                query=query,
                parameters=[
                    {"name": "@user_id", "value": user_id},
                    {"name": "@repo_id", "value": repository_id}
                ],
                partition_key=user_id,
                max_item_count=limit
            )

            summaries = []
            async for item in items:
                conv = Conversation.from_cosmos_document(item)
                summaries.append(ConversationSummary.from_conversation(conv))

            return summaries

        except Exception as e:
            self.logger.error(
                "Failed to get repository conversations",
                error=str(e)
            )
            raise CosmosDBError(
                f"Query failed: {e}",
                operation="get_conversations_by_repository"
            )

    # =========================================================================
    # Utility Operations
    # =========================================================================

    async def archive_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> bool:
        """
        Archive a conversation.

        Args:
            conversation_id: UUID of the conversation
            user_id: User ID

        Returns:
            True if archived successfully
        """
        conversation = await self.get_conversation(conversation_id, user_id)

        if not conversation:
            return False

        conversation.is_archived = True
        await self.update_conversation(conversation)

        return True

    async def get_user_stats(self, user_id: str) -> dict[str, Any]:
        """
        Get statistics for a user's conversations.

        Args:
            user_id: User ID

        Returns:
            Statistics dict
        """
        try:
            query = """
            SELECT
                COUNT(1) as total_conversations,
                SUM(c.total_tokens) as total_tokens,
                SUM(ARRAY_LENGTH(c.messages)) as total_messages
            FROM c
            WHERE c.user_id = @user_id
            """

            items = self.container.query_items(
                query=query,
                parameters=[{"name": "@user_id", "value": user_id}],
                partition_key=user_id
            )

            async for item in items:
                return {
                    "total_conversations": item.get("total_conversations", 0),
                    "total_tokens": item.get("total_tokens", 0),
                    "total_messages": item.get("total_messages", 0)
                }

            return {
                "total_conversations": 0,
                "total_tokens": 0,
                "total_messages": 0
            }

        except Exception as e:
            self.logger.error("Failed to get user stats", error=str(e))
            return {"error": str(e)}

    async def health_check(self) -> bool:
        """
        Check if Cosmos DB is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to read database properties
            await self._database.read()
            return True
        except Exception as e:
            self.logger.error("Cosmos DB health check failed", error=str(e))
            return False
