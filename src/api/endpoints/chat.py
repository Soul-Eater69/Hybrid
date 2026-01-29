"""
Chat Endpoints
==============

Endpoints for chat conversation management.

ENDPOINTS:
    POST /chat/conversations          - Create conversation
    GET /chat/conversations           - List conversations
    GET /chat/conversations/{id}      - Get conversation
    DELETE /chat/conversations/{id}   - Delete conversation
    POST /chat/conversations/{id}/messages - Send message

DATA FLOW:
    User Message
          ↓
    ChatService.send_message()
          ↓
    Gather Context (Vector + Neo4j)
          ↓
    Generate Response (LLM)
          ↓
    Save to Cosmos DB
          ↓
    Return Response

USAGE:
    # Create a conversation
    curl -X POST http://localhost:8000/api/v1/chat/conversations \\
         -H "Content-Type: application/json" \\
         -d '{
             "user_id": "user-123",
             "repository_id": "repo-456"
         }'

    # Send a message
    curl -X POST http://localhost:8000/api/v1/chat/conversations/{id}/messages \\
         -H "Content-Type: application/json" \\
         -d '{
             "user_id": "user-123",
             "content": "How do I validate emails?"
         }'
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any

from pydantic import BaseModel, Field

from src.api.dependencies import get_chat_service
from src.services.chat_service import ChatService

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""

    user_id: str = Field(
        description="User ID",
        examples=["user-123"]
    )
    repository_id: str | None = Field(
        default=None,
        description="Optional repository to discuss",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    initial_message: str | None = Field(
        default=None,
        description="Optional first message to start conversation",
        examples=["How do I validate user input in this codebase?"]
    )


class SendMessageRequest(BaseModel):
    """Request to send a message."""

    user_id: str = Field(
        description="User ID",
        examples=["user-123"]
    )
    content: str = Field(
        description="Message content",
        min_length=1,
        examples=["How do I validate email addresses?"]
    )
    repository_id: str | None = Field(
        default=None,
        description="Repository context (uses conversation default if not specified)"
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/conversations",
    response_model=dict[str, Any],
    summary="Create Conversation",
    description="Create a new chat conversation, optionally with an initial message"
)
async def create_conversation(
    request: CreateConversationRequest,
    chat_service: ChatService = Depends(get_chat_service)
) -> dict[str, Any]:
    """
    Create a new chat conversation.

    Optionally provide an initial message to start the conversation
    with an AI response.

    Args:
        request: Conversation creation request
        chat_service: Chat service dependency

    Returns:
        Created conversation details

    Example Request:
        {
            "user_id": "user-123",
            "repository_id": "repo-456",
            "initial_message": "Help me understand the validation functions"
        }

    Example Response:
        {
            "conversation_id": "conv-789",
            "title": "Help me understand the validation...",
            "repository_id": "repo-456",
            "response": {
                "content": "I can help you understand...",
                "message_type": "text"
            }
        }
    """
    try:
        result = await chat_service.create_conversation(
            user_id=request.user_id,
            repository_id=request.repository_id,
            initial_message=request.initial_message
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/conversations",
    response_model=list[dict[str, Any]],
    summary="List Conversations",
    description="List all conversations for a user"
)
async def list_conversations(
    user_id: str = Query(description="User ID"),
    repository_id: str | None = Query(default=None, description="Filter by repository"),
    limit: int = Query(default=50, le=100, description="Maximum results"),
    chat_service: ChatService = Depends(get_chat_service)
) -> list[dict[str, Any]]:
    """
    List conversations for a user.

    Optionally filter by repository.

    Args:
        user_id: User ID
        repository_id: Optional repository filter
        limit: Maximum results
        chat_service: Chat service dependency

    Returns:
        List of conversation summaries
    """
    try:
        return await chat_service.list_conversations(
            user_id=user_id,
            repository_id=repository_id,
            limit=limit
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/conversations/{conversation_id}",
    response_model=dict[str, Any],
    summary="Get Conversation",
    description="Get a conversation with all messages"
)
async def get_conversation(
    conversation_id: str,
    user_id: str = Query(description="User ID"),
    chat_service: ChatService = Depends(get_chat_service)
) -> dict[str, Any]:
    """
    Get a conversation with full message history.

    Args:
        conversation_id: Conversation UUID
        user_id: User ID (for authorization)
        chat_service: Chat service dependency

    Returns:
        Full conversation with messages
    """
    try:
        conversation = await chat_service.get_conversation(
            conversation_id=conversation_id,
            user_id=user_id
        )

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return conversation

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/conversations/{conversation_id}",
    summary="Delete Conversation",
    description="Delete a conversation and all its messages"
)
async def delete_conversation(
    conversation_id: str,
    user_id: str = Query(description="User ID"),
    chat_service: ChatService = Depends(get_chat_service)
) -> dict[str, str]:
    """
    Delete a conversation.

    Args:
        conversation_id: Conversation UUID
        user_id: User ID
        chat_service: Chat service dependency

    Returns:
        Deletion confirmation
    """
    try:
        deleted = await chat_service.delete_conversation(
            conversation_id=conversation_id,
            user_id=user_id
        )

        if not deleted:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {
            "message": "Conversation deleted successfully",
            "conversation_id": conversation_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=dict[str, Any],
    summary="Send Message",
    description="Send a message and receive an AI response"
)
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    chat_service: ChatService = Depends(get_chat_service)
) -> dict[str, Any]:
    """
    Send a message to a conversation and get an AI response.

    The AI response includes:
    - Context-aware answer based on codebase
    - Referenced code entities
    - Code examples if relevant

    Args:
        conversation_id: Conversation UUID
        request: Message request
        chat_service: Chat service dependency

    Returns:
        AI response with metadata

    Example Request:
        {
            "user_id": "user-123",
            "content": "How can I improve the error handling in validate_email?"
        }

    Example Response:
        {
            "message_id": "msg-456",
            "content": "Looking at the validate_email function in validators.py...",
            "message_type": "text",
            "code_references": [
                {"entity_id": "...", "name": "validate_email"}
            ],
            "tokens_used": 150
        }
    """
    try:
        response = await chat_service.send_message(
            conversation_id=conversation_id,
            user_id=request.user_id,
            content=request.content,
            repository_id=request.repository_id
        )
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
