"""
Conversation Models
===================

Defines models for chat conversations and messages.
Conversations are stored in Azure Cosmos DB for persistence.

HOW IT WORKS:
    1. User starts a conversation about a repository
    2. Messages are stored with context (code entities, search results)
    3. AI responses include generated code, impact analysis, etc.
    4. Full conversation history enables context-aware follow-ups

DATA STRUCTURE IN COSMOS DB:
    Container: conversations
    Partition Key: /user_id

    Document Structure:
    {
        "id": "conversation-uuid",
        "user_id": "user-123",
        "repository_id": "repo-uuid",
        "title": "Discussion about validate_email",
        "messages": [...],
        "metadata": {...},
        "created_at": "2024-01-29T10:30:00Z",
        "updated_at": "2024-01-29T10:45:00Z"
    }

USAGE:
    from src.models.conversation import Conversation, Message

    # Create a conversation
    conv = Conversation(
        user_id="user-123",
        repository_id="repo-456",
        title="Help with validation functions"
    )

    # Add a message
    conv.add_message(Message(
        role="user",
        content="How do I validate email addresses?"
    ))
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """
    Roles for conversation messages.

    - USER: Message from the user
    - ASSISTANT: Response from the AI
    - SYSTEM: System messages (context, errors)
    """

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, Enum):
    """
    Types of messages for specialized handling.

    - TEXT: Regular text message
    - CODE: Generated code
    - SEARCH_RESULT: Semantic search results
    - IMPACT_RESULT: Impact analysis results
    - ERROR: Error message
    """

    TEXT = "text"
    CODE = "code"
    SEARCH_RESULT = "search_result"
    IMPACT_RESULT = "impact_result"
    CODE_GENERATION = "code_generation"
    ERROR = "error"


class CodeContext(BaseModel):
    """
    Context about code entities referenced in a message.

    Used to track which code entities were discussed or generated.

    Attributes:
        entity_ids: UUIDs of referenced entities
        file_paths: Files discussed
        search_query: If this was a search, the query used
        generated_code: If code was generated, the code
    """

    entity_ids: list[str] = Field(
        default_factory=list,
        description="UUIDs of referenced code entities"
    )
    file_paths: list[str] = Field(
        default_factory=list,
        description="File paths discussed"
    )
    search_query: str | None = Field(
        default=None,
        description="Search query if applicable"
    )
    generated_code: str | None = Field(
        default=None,
        description="Generated code if applicable"
    )
    impact_analysis_id: str | None = Field(
        default=None,
        description="Impact analysis ID if applicable"
    )


class Message(BaseModel):
    """
    A single message in a conversation.

    Can be from the user, assistant, or system.
    Includes optional code context for tracking references.

    Attributes:
        id: Unique message identifier
        role: Who sent the message (user/assistant/system)
        content: The message text content
        message_type: Type of message for rendering
        code_context: Optional code-related context
        metadata: Additional metadata
        created_at: When the message was sent
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique message identifier"
    )
    role: MessageRole = Field(
        description="Who sent the message"
    )
    content: str = Field(
        description="Message text content"
    )
    message_type: MessageType = Field(
        default=MessageType.TEXT,
        description="Type of message"
    )
    code_context: CodeContext | None = Field(
        default=None,
        description="Code-related context"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    tokens_used: int = Field(
        default=0,
        description="Tokens used for this message (if AI response)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the message was sent"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Cosmos DB storage."""
        return {
            "id": str(self.id),
            "role": self.role,
            "content": self.content,
            "message_type": self.message_type,
            "code_context": self.code_context.model_dump() if self.code_context else None,
            "metadata": self.metadata,
            "tokens_used": self.tokens_used,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        """Create Message from Cosmos DB document."""
        code_context = None
        if data.get("code_context"):
            code_context = CodeContext(**data["code_context"])

        return cls(
            id=UUID(data["id"]),
            role=MessageRole(data["role"]),
            content=data["content"],
            message_type=MessageType(data.get("message_type", "text")),
            code_context=code_context,
            metadata=data.get("metadata", {}),
            tokens_used=data.get("tokens_used", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


class Conversation(BaseModel):
    """
    A conversation about code in a repository.

    Stores the full message history and context.

    Attributes:
        id: Unique conversation identifier
        user_id: ID of the user who owns this conversation
        repository_id: Repository being discussed
        title: Conversation title (auto-generated or user-set)
        messages: List of messages in chronological order
        metadata: Additional metadata
        is_archived: Whether the conversation is archived
        created_at: When the conversation started
        updated_at: Last activity timestamp
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique conversation identifier"
    )
    user_id: str = Field(
        description="ID of the user"
    )
    repository_id: str | None = Field(
        default=None,
        description="Repository being discussed"
    )
    title: str = Field(
        default="New Conversation",
        description="Conversation title"
    )
    messages: list[Message] = Field(
        default_factory=list,
        description="Messages in chronological order"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    is_archived: bool = Field(
        default=False,
        description="Whether the conversation is archived"
    )
    total_tokens: int = Field(
        default=0,
        description="Total tokens used in this conversation"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the conversation started"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last activity timestamp"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True

    def add_message(self, message: Message) -> None:
        """
        Add a message to the conversation.

        Updates the conversation's updated_at timestamp
        and total token count.

        Args:
            message: Message to add
        """
        self.messages.append(message)
        self.total_tokens += message.tokens_used
        self.updated_at = datetime.utcnow()

        # Auto-generate title from first user message
        if self.title == "New Conversation" and message.role == MessageRole.USER:
            self.title = message.content[:50] + ("..." if len(message.content) > 50 else "")

    def get_context_window(self, max_messages: int = 20) -> list[Message]:
        """
        Get recent messages for context.

        Returns the most recent messages up to max_messages.

        Args:
            max_messages: Maximum number of messages to return

        Returns:
            List of recent messages
        """
        return self.messages[-max_messages:]

    def to_cosmos_document(self) -> dict[str, Any]:
        """
        Convert to Cosmos DB document format.

        Returns:
            Dictionary suitable for Cosmos DB storage
        """
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "repository_id": self.repository_id,
            "title": self.title,
            "messages": [msg.to_dict() for msg in self.messages],
            "metadata": self.metadata,
            "is_archived": self.is_archived,
            "total_tokens": self.total_tokens,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_cosmos_document(cls, doc: dict[str, Any]) -> "Conversation":
        """
        Create Conversation from Cosmos DB document.

        Args:
            doc: Cosmos DB document

        Returns:
            Conversation instance
        """
        messages = [
            Message.from_dict(msg_data)
            for msg_data in doc.get("messages", [])
        ]

        return cls(
            id=UUID(doc["id"]),
            user_id=doc["user_id"],
            repository_id=doc.get("repository_id"),
            title=doc.get("title", "New Conversation"),
            messages=messages,
            metadata=doc.get("metadata", {}),
            is_archived=doc.get("is_archived", False),
            total_tokens=doc.get("total_tokens", 0),
            created_at=datetime.fromisoformat(doc["created_at"]),
            updated_at=datetime.fromisoformat(doc["updated_at"]),
        )

    @property
    def message_count(self) -> int:
        """Get the total number of messages."""
        return len(self.messages)

    @property
    def last_message(self) -> Message | None:
        """Get the last message in the conversation."""
        return self.messages[-1] if self.messages else None


class ConversationSummary(BaseModel):
    """
    Summary of a conversation for listing.

    Lightweight model for displaying conversation lists.

    Attributes:
        id: Conversation ID
        title: Conversation title
        repository_id: Repository being discussed
        message_count: Number of messages
        last_message_preview: Preview of last message
        updated_at: Last activity
    """

    id: str = Field(description="Conversation ID")
    title: str = Field(description="Conversation title")
    repository_id: str | None = Field(default=None, description="Repository ID")
    message_count: int = Field(description="Number of messages")
    last_message_preview: str | None = Field(
        default=None,
        description="Preview of last message"
    )
    is_archived: bool = Field(default=False, description="Is archived")
    updated_at: datetime = Field(description="Last activity")

    @classmethod
    def from_conversation(cls, conv: Conversation) -> "ConversationSummary":
        """Create summary from full conversation."""
        last_preview = None
        if conv.last_message:
            content = conv.last_message.content
            last_preview = content[:100] + ("..." if len(content) > 100 else "")

        return cls(
            id=str(conv.id),
            title=conv.title,
            repository_id=conv.repository_id,
            message_count=conv.message_count,
            last_message_preview=last_preview,
            is_archived=conv.is_archived,
            updated_at=conv.updated_at,
        )
