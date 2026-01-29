"""
Chat Service
============

Orchestrates chat interactions combining:
- Conversation persistence (Cosmos DB)
- Code context (Neo4j + Vector DB)
- AI responses (LangChain)

HOW IT WORKS:
    1. User sends a message
    2. Retrieve conversation history
    3. Gather code context (search, entities)
    4. Build prompt with history + context
    5. Generate AI response
    6. Save response to conversation
    7. Return response

DATA FLOW:
    User Message
          ↓
    ┌─────────────────────────────────────────┐
    │           Load Context                   │
    │                                          │
    │  Cosmos DB: Conversation history         │
    │  Vector DB: Similar code                 │
    │  Neo4j: Related entities                 │
    └─────────────────────────────────────────┘
          ↓
    ┌─────────────────────────────────────────┐
    │         Build Prompt                     │
    │                                          │
    │  System: "You are a code assistant..."   │
    │  History: [prev messages]                │
    │  Context: [similar code, entities]       │
    │  User: [current message]                 │
    └─────────────────────────────────────────┘
          ↓
    ┌─────────────────────────────────────────┐
    │           LLM Generation                 │
    │                                          │
    │  GPT-4 generates contextual response     │
    └─────────────────────────────────────────┘
          ↓
    ┌─────────────────────────────────────────┐
    │         Save & Return                    │
    │                                          │
    │  Save to Cosmos DB                       │
    │  Return response to user                 │
    └─────────────────────────────────────────┘

USAGE:
    from src.services.chat_service import ChatService

    chat = ChatService(cosmos, neo4j, vector, generator)

    # Send a message
    response = await chat.send_message(
        conversation_id="...",
        user_id="user-123",
        content="How do I validate emails in this codebase?"
    )
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI

from src.core.config import settings
from src.core.logging import LoggerMixin
from src.models.conversation import (
    CodeContext,
    Conversation,
    Message,
    MessageRole,
    MessageType,
)
from src.services.cosmos_service import CosmosService
from src.services.neo4j_service import Neo4jService
from src.services.vector_service import VectorService
from src.services.code_generator import CodeGenerator


# System prompt for the chat assistant
CHAT_SYSTEM_PROMPT = """You are an intelligent code assistant helping developers understand and work with their codebase.

You have access to:
1. The codebase's knowledge graph (functions, classes, relationships)
2. Semantic search over code (find code by meaning)
3. Impact analysis (understand change effects)
4. Code generation (create new code following existing patterns)

When answering questions:
- Be concise but thorough
- Reference specific files, functions, and line numbers when relevant
- If code examples would help, provide them
- If you're unsure, say so and suggest how to find out

The user is working with the following repository: {repository_name}

Current context from the codebase:
{code_context}
"""


class ChatService(LoggerMixin):
    """
    Service for handling chat interactions.

    Orchestrates conversation flow with code context.

    Attributes:
        cosmos: Cosmos DB service for persistence
        neo4j: Neo4j service for graph queries
        vector: Vector service for semantic search
        generator: Code generator service
        llm: LangChain LLM for chat
    """

    def __init__(
        self,
        cosmos: CosmosService,
        neo4j: Neo4jService,
        vector: VectorService,
        generator: CodeGenerator
    ) -> None:
        """
        Initialize the chat service.

        Args:
            cosmos: Cosmos DB service
            neo4j: Neo4j service
            vector: Vector service
            generator: Code generator service
        """
        self.cosmos = cosmos
        self.neo4j = neo4j
        self.vector = vector
        self.generator = generator

        # Initialize LLM for chat
        self._llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.7,
            api_key=settings.openai_api_key,
            max_tokens=2000
        )

    async def create_conversation(
        self,
        user_id: str,
        repository_id: str | None = None,
        initial_message: str | None = None
    ) -> dict[str, Any]:
        """
        Create a new conversation.

        Args:
            user_id: User ID
            repository_id: Optional repository context
            initial_message: Optional first message

        Returns:
            Conversation details and optional first response
        """
        # Create conversation
        conversation = await self.cosmos.create_conversation(
            user_id=user_id,
            repository_id=repository_id
        )

        result = {
            "conversation_id": str(conversation.id),
            "title": conversation.title,
            "repository_id": repository_id,
            "created_at": conversation.created_at.isoformat()
        }

        # Process initial message if provided
        if initial_message:
            response = await self.send_message(
                conversation_id=str(conversation.id),
                user_id=user_id,
                content=initial_message,
                repository_id=repository_id
            )
            result["response"] = response

        return result

    async def send_message(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
        repository_id: str | None = None
    ) -> dict[str, Any]:
        """
        Send a message and get a response.

        Args:
            conversation_id: Conversation UUID
            user_id: User ID
            content: Message content
            repository_id: Repository context

        Returns:
            AI response with context
        """
        self.logger.info(
            "Processing chat message",
            conversation_id=conversation_id,
            content_preview=content[:100]
        )

        # Get or create conversation
        conversation = await self.cosmos.get_conversation(
            conversation_id,
            user_id
        )

        if not conversation:
            # Create if not exists
            conversation = await self.cosmos.create_conversation(
                user_id=user_id,
                repository_id=repository_id
            )

        # Use repository from conversation if not specified
        repo_id = repository_id or conversation.repository_id

        # Create user message
        user_message = Message(
            role=MessageRole.USER,
            content=content,
            message_type=MessageType.TEXT
        )

        # Add to conversation
        conversation.add_message(user_message)

        # Gather code context
        code_context = await self._gather_context(content, repo_id)

        # Build messages for LLM
        llm_messages = self._build_llm_messages(
            conversation,
            code_context,
            repo_id
        )

        # Generate response
        try:
            response = await self._generate_response(llm_messages)
            response_content = response.content
            tokens_used = response.response_metadata.get("token_usage", {}).get("total_tokens", 0)

        except Exception as e:
            self.logger.error("LLM generation failed", error=str(e))
            response_content = f"I encountered an error processing your request: {str(e)}"
            tokens_used = 0

        # Determine message type based on content
        message_type = self._determine_message_type(response_content)

        # Create assistant message
        assistant_message = Message(
            role=MessageRole.ASSISTANT,
            content=response_content,
            message_type=message_type,
            code_context=CodeContext(
                entity_ids=[r["entity_id"] for r in code_context.get("similar_code", [])],
                search_query=content
            ),
            tokens_used=tokens_used
        )

        # Add to conversation
        conversation.add_message(assistant_message)

        # Save conversation
        await self.cosmos.update_conversation(conversation)

        return {
            "message_id": str(assistant_message.id),
            "content": response_content,
            "message_type": message_type,
            "tokens_used": tokens_used,
            "code_references": code_context.get("similar_code", [])[:3],
            "created_at": assistant_message.created_at.isoformat()
        }

    async def _gather_context(
        self,
        query: str,
        repository_id: str | None
    ) -> dict[str, Any]:
        """
        Gather relevant code context for the query.

        Args:
            query: User's query
            repository_id: Repository ID

        Returns:
            Context dict with similar code and entities
        """
        context = {
            "similar_code": [],
            "related_entities": []
        }

        if not repository_id:
            return context

        try:
            # Search for similar code
            search_results = await self.vector.search(
                query=query,
                repository_id=repository_id,
                limit=5
            )
            context["similar_code"] = search_results

        except Exception as e:
            self.logger.warning(f"Context search failed: {e}")

        return context

    def _build_llm_messages(
        self,
        conversation: Conversation,
        code_context: dict[str, Any],
        repository_id: str | None
    ) -> list:
        """
        Build message list for LLM.

        Args:
            conversation: Conversation with history
            code_context: Gathered code context
            repository_id: Repository ID

        Returns:
            List of LangChain messages
        """
        messages = []

        # Format code context
        context_str = ""
        if code_context.get("similar_code"):
            context_str = "Relevant code found:\n"
            for result in code_context["similar_code"][:3]:
                meta = result.get("metadata", {})
                context_str += f"\n- {meta.get('name', 'unknown')} in {meta.get('file_path', 'unknown')}\n"

        # System message
        system_content = CHAT_SYSTEM_PROMPT.format(
            repository_name=repository_id or "No repository selected",
            code_context=context_str or "No specific code context available."
        )
        messages.append(SystemMessage(content=system_content))

        # Add conversation history (limited to recent messages)
        history = conversation.get_context_window(max_messages=10)
        for msg in history[:-1]:  # Exclude the current message
            if msg.role == MessageRole.USER:
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                messages.append(AIMessage(content=msg.content))

        # Add current user message
        if history:
            current = history[-1]
            if current.role == MessageRole.USER:
                messages.append(HumanMessage(content=current.content))

        return messages

    async def _generate_response(self, messages: list) -> Any:
        """
        Generate response from LLM.

        Args:
            messages: List of LangChain messages

        Returns:
            LLM response
        """
        import asyncio
        return await asyncio.to_thread(self._llm.invoke, messages)

    def _determine_message_type(self, content: str) -> MessageType:
        """
        Determine the message type based on content.

        Args:
            content: Response content

        Returns:
            MessageType enum value
        """
        # Check for code blocks
        if "```" in content:
            return MessageType.CODE

        return MessageType.TEXT

    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> dict[str, Any] | None:
        """
        Get a conversation with all messages.

        Args:
            conversation_id: Conversation UUID
            user_id: User ID

        Returns:
            Conversation dict or None
        """
        conversation = await self.cosmos.get_conversation(
            conversation_id,
            user_id
        )

        if not conversation:
            return None

        return {
            "id": str(conversation.id),
            "title": conversation.title,
            "repository_id": conversation.repository_id,
            "messages": [
                {
                    "id": str(msg.id),
                    "role": msg.role,
                    "content": msg.content,
                    "message_type": msg.message_type,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in conversation.messages
            ],
            "total_tokens": conversation.total_tokens,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat()
        }

    async def list_conversations(
        self,
        user_id: str,
        repository_id: str | None = None,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        List user's conversations.

        Args:
            user_id: User ID
            repository_id: Filter by repository
            limit: Maximum results

        Returns:
            List of conversation summaries
        """
        if repository_id:
            summaries = await self.cosmos.get_conversations_by_repository(
                user_id,
                repository_id,
                limit
            )
        else:
            summaries = await self.cosmos.list_conversations(
                user_id,
                limit=limit
            )

        return [
            {
                "id": s.id,
                "title": s.title,
                "repository_id": s.repository_id,
                "message_count": s.message_count,
                "last_message_preview": s.last_message_preview,
                "updated_at": s.updated_at.isoformat()
            }
            for s in summaries
        ]

    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: Conversation UUID
            user_id: User ID

        Returns:
            True if deleted
        """
        return await self.cosmos.delete_conversation(conversation_id, user_id)
