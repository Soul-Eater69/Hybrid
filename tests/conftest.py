"""
Test Configuration
==================

Pytest fixtures and configuration for testing.

HOW TO USE:
    Fixtures defined here are automatically available
    to all test files in this directory.

RUNNING TESTS:
    pytest                    # Run all tests
    pytest -v                 # Verbose output
    pytest --cov=src          # With coverage
    pytest tests/test_parser.py  # Specific file
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_neo4j():
    """Create a mock Neo4j service."""
    mock = AsyncMock()
    mock.health_check.return_value = True
    mock.get_entity_by_id.return_value = {
        "id": "test-id",
        "name": "test_function",
        "entity_type": "function",
        "file_path": "test.py"
    }
    return mock


@pytest.fixture
def mock_vector():
    """Create a mock Vector service."""
    mock = AsyncMock()
    mock.health_check.return_value = True
    mock.search.return_value = [
        {
            "entity_id": "test-id",
            "score": 0.9,
            "metadata": {"name": "test_function"}
        }
    ]
    return mock


@pytest.fixture
def mock_cosmos():
    """Create a mock Cosmos DB service."""
    mock = AsyncMock()
    mock.health_check.return_value = True
    return mock


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing parsing."""
    return '''
"""Sample module docstring."""

import os
from typing import Optional


def validate_email(email: str) -> bool:
    """Validate an email address.

    Args:
        email: The email to validate

    Returns:
        True if valid, False otherwise
    """
    return "@" in email and "." in email


class UserValidator:
    """Validates user data."""

    def __init__(self, strict: bool = False):
        """Initialize validator.

        Args:
            strict: Whether to use strict validation
        """
        self.strict = strict

    def validate_username(self, username: str) -> bool:
        """Validate a username.

        Args:
            username: The username to validate

        Returns:
            True if valid
        """
        if len(username) < 3:
            return False
        return username.isalnum()

    def validate_all(self, email: str, username: str) -> bool:
        """Validate all fields."""
        return validate_email(email) and self.validate_username(username)


MAX_RETRIES = 3
'''


@pytest.fixture
def sample_entities():
    """Sample code entities for testing."""
    from src.models.code_entity import FunctionEntity, ClassEntity
    from uuid import uuid4

    func = FunctionEntity(
        id=uuid4(),
        name="validate_email",
        qualified_name="validators.validate_email",
        file_path="validators.py",
        start_line=10,
        end_line=20,
        source_code="def validate_email(email): return '@' in email",
        signature="def validate_email(email: str) -> bool",
        parameters=[{"name": "email", "type": "str"}],
        return_type="bool"
    )

    cls = ClassEntity(
        id=uuid4(),
        name="UserValidator",
        qualified_name="validators.UserValidator",
        file_path="validators.py",
        start_line=25,
        end_line=50,
        source_code="class UserValidator: ...",
        bases=[],
        methods=["validate_username", "validate_all"]
    )

    return [func, cls]
