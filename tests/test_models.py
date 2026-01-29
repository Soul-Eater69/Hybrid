"""
Model Tests
===========

Tests for data models.
"""

import pytest
from uuid import uuid4
from datetime import datetime

from src.models.code_entity import (
    CodeEntity,
    CodeEntityType,
    FunctionEntity,
    ClassEntity,
    ModuleEntity,
)
from src.models.relationship import (
    Relationship,
    RelationshipType,
    INVERSE_RELATIONSHIPS,
)
from src.models.impact import (
    ImpactAnalysis,
    ImpactedEntity,
    ImpactLevel,
)
from src.models.conversation import (
    Conversation,
    Message,
    MessageRole,
    MessageType,
    ConversationSummary,
)


class TestCodeEntityModels:
    """Tests for code entity models."""

    def test_function_entity_creation(self):
        """Test creating a FunctionEntity."""
        func = FunctionEntity(
            name="test_func",
            qualified_name="module.test_func",
            file_path="test.py",
            start_line=10,
            end_line=20,
            source_code="def test_func(): pass",
            signature="def test_func() -> None",
            parameters=[{"name": "x", "type": "int"}],
            return_type="None",
            is_async=False,
            decorators=["staticmethod"]
        )

        assert func.name == "test_func"
        assert func.entity_type == CodeEntityType.FUNCTION
        assert func.is_async is False
        assert "staticmethod" in func.decorators

    def test_class_entity_creation(self):
        """Test creating a ClassEntity."""
        cls = ClassEntity(
            name="TestClass",
            qualified_name="module.TestClass",
            file_path="test.py",
            start_line=1,
            end_line=50,
            source_code="class TestClass: ...",
            bases=["BaseClass"],
            methods=["method1", "method2"],
            is_dataclass=True
        )

        assert cls.name == "TestClass"
        assert cls.entity_type == CodeEntityType.CLASS
        assert "BaseClass" in cls.bases
        assert cls.is_dataclass is True

    def test_entity_to_neo4j_properties(self):
        """Test conversion to Neo4j properties."""
        func = FunctionEntity(
            name="test",
            file_path="test.py",
            start_line=1,
            end_line=5,
            source_code="def test(): pass"
        )

        props = func.to_neo4j_properties()

        assert "id" in props
        assert props["name"] == "test"
        assert props["entity_type"] == "function"
        assert "created_at" in props

    def test_entity_to_embedding_document(self):
        """Test conversion to embedding document."""
        func = FunctionEntity(
            name="validate_email",
            qualified_name="validators.validate_email",
            file_path="validators.py",
            start_line=1,
            end_line=5,
            source_code="def validate_email(email): return '@' in email",
            docstring="Validates email addresses"
        )

        doc = func.to_embedding_document()

        assert "FUNCTION" in doc
        assert "validate_email" in doc
        assert "validators.py" in doc
        assert "Validates email addresses" in doc


class TestRelationshipModels:
    """Tests for relationship models."""

    def test_relationship_creation(self):
        """Test creating a Relationship."""
        rel = Relationship(
            source_id=uuid4(),
            target_id=uuid4(),
            relationship_type=RelationshipType.CALLS,
            weight=0.9,
            file_path="test.py",
            line_number=42
        )

        assert rel.relationship_type == RelationshipType.CALLS
        assert rel.weight == 0.9
        assert rel.line_number == 42

    def test_relationship_inverse(self):
        """Test getting inverse relationship."""
        rel = Relationship(
            source_id=uuid4(),
            target_id=uuid4(),
            relationship_type=RelationshipType.CALLS,
        )

        inverse = rel.get_inverse()

        assert inverse.source_id == rel.target_id
        assert inverse.target_id == rel.source_id
        assert inverse.relationship_type == RelationshipType.CALLED_BY

    def test_all_relationships_have_inverse(self):
        """Verify all relationship types have an inverse defined."""
        for rel_type in RelationshipType:
            assert rel_type in INVERSE_RELATIONSHIPS


class TestImpactModels:
    """Tests for impact analysis models."""

    def test_impacted_entity_creation(self):
        """Test creating an ImpactedEntity."""
        entity = ImpactedEntity(
            entity_id=uuid4(),
            entity_name="process_data",
            entity_type=CodeEntityType.FUNCTION,
            file_path="processor.py",
            impact_level=ImpactLevel.DIRECT,
            impact_score=8.5,
            distance=1,
            reason="Directly calls the changed function"
        )

        assert entity.impact_level == ImpactLevel.DIRECT
        assert entity.impact_score == 8.5
        assert entity.distance == 1

    def test_impact_analysis_counts(self):
        """Test ImpactAnalysis count properties."""
        analysis = ImpactAnalysis(
            source_entity_id=uuid4(),
            source_entity_name="test",
            source_file_path="test.py",
            impacted_entities=[
                ImpactedEntity(
                    entity_id=uuid4(),
                    entity_name="e1",
                    entity_type=CodeEntityType.FUNCTION,
                    file_path="a.py",
                    impact_level=ImpactLevel.CRITICAL,
                    impact_score=9,
                    distance=1
                ),
                ImpactedEntity(
                    entity_id=uuid4(),
                    entity_name="e2",
                    entity_type=CodeEntityType.FUNCTION,
                    file_path="b.py",
                    impact_level=ImpactLevel.DIRECT,
                    impact_score=7,
                    distance=1
                ),
                ImpactedEntity(
                    entity_id=uuid4(),
                    entity_name="e3",
                    entity_type=CodeEntityType.FUNCTION,
                    file_path="c.py",
                    impact_level=ImpactLevel.INDIRECT,
                    impact_score=4,
                    distance=2
                ),
            ]
        )

        assert analysis.critical_count == 1
        assert analysis.direct_count == 1
        assert analysis.indirect_count == 1
        assert analysis.total_count == 3


class TestConversationModels:
    """Tests for conversation models."""

    def test_message_creation(self):
        """Test creating a Message."""
        msg = Message(
            role=MessageRole.USER,
            content="How do I validate emails?",
            message_type=MessageType.TEXT
        )

        assert msg.role == MessageRole.USER
        assert "validate" in msg.content
        assert msg.message_type == MessageType.TEXT

    def test_conversation_add_message(self):
        """Test adding messages to a conversation."""
        conv = Conversation(
            user_id="user-123",
            repository_id="repo-456"
        )

        assert conv.message_count == 0

        msg = Message(
            role=MessageRole.USER,
            content="Hello"
        )
        conv.add_message(msg)

        assert conv.message_count == 1
        assert conv.last_message == msg

    def test_conversation_auto_title(self):
        """Test automatic title generation."""
        conv = Conversation(
            user_id="user-123"
        )

        assert conv.title == "New Conversation"

        conv.add_message(Message(
            role=MessageRole.USER,
            content="How do I implement validation for user input fields?"
        ))

        # Title should be updated from first user message
        assert conv.title != "New Conversation"
        assert len(conv.title) <= 53  # 50 chars + "..."

    def test_conversation_to_cosmos_document(self):
        """Test conversion to Cosmos DB document."""
        conv = Conversation(
            user_id="user-123",
            repository_id="repo-456",
            title="Test conversation"
        )

        conv.add_message(Message(
            role=MessageRole.USER,
            content="Test message"
        ))

        doc = conv.to_cosmos_document()

        assert doc["user_id"] == "user-123"
        assert doc["repository_id"] == "repo-456"
        assert len(doc["messages"]) == 1
        assert "created_at" in doc

    def test_conversation_from_cosmos_document(self):
        """Test creating Conversation from Cosmos document."""
        doc = {
            "id": str(uuid4()),
            "user_id": "user-123",
            "repository_id": "repo-456",
            "title": "Test",
            "messages": [
                {
                    "id": str(uuid4()),
                    "role": "user",
                    "content": "Hello",
                    "message_type": "text",
                    "tokens_used": 0,
                    "created_at": datetime.utcnow().isoformat()
                }
            ],
            "is_archived": False,
            "total_tokens": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        conv = Conversation.from_cosmos_document(doc)

        assert conv.user_id == "user-123"
        assert conv.message_count == 1
        assert conv.messages[0].content == "Hello"

    def test_conversation_summary(self):
        """Test ConversationSummary creation."""
        conv = Conversation(
            user_id="user-123",
            title="Test conversation"
        )
        conv.add_message(Message(
            role=MessageRole.USER,
            content="This is a test message"
        ))

        summary = ConversationSummary.from_conversation(conv)

        assert summary.title == "Test conversation"
        assert summary.message_count == 1
        assert summary.last_message_preview is not None
