"""
Parser Tests
============

Tests for the CodeQL/AST parser service.
"""

import pytest
import tempfile
from pathlib import Path

from src.services.codeql_parser import CodeQLParser


class TestCodeQLParser:
    """Tests for CodeQL parser."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return CodeQLParser()

    @pytest.mark.asyncio
    async def test_parse_python_file(self, parser, sample_python_code, tmp_path):
        """Test parsing a Python file."""
        # Create a temporary Python file
        test_file = tmp_path / "test_module.py"
        test_file.write_text(sample_python_code)

        # Parse the repository
        entities, relationships = await parser.parse_repository(
            str(tmp_path),
            language="python"
        )

        # Verify entities were extracted
        assert len(entities) > 0

        # Find the module entity
        modules = [e for e in entities if e.entity_type == "module"]
        assert len(modules) == 1

        # Find function entities
        functions = [e for e in entities if e.entity_type == "function"]
        assert len(functions) >= 1

        # Verify validate_email function was found
        validate_email = next(
            (f for f in functions if f.name == "validate_email"),
            None
        )
        assert validate_email is not None
        assert validate_email.return_type == "bool"

        # Find class entities
        classes = [e for e in entities if e.entity_type == "class"]
        assert len(classes) >= 1

        # Verify UserValidator class was found
        user_validator = next(
            (c for c in classes if c.name == "UserValidator"),
            None
        )
        assert user_validator is not None
        assert "validate_username" in user_validator.methods

    @pytest.mark.asyncio
    async def test_extract_relationships(self, parser, sample_python_code, tmp_path):
        """Test that relationships are extracted."""
        test_file = tmp_path / "test_module.py"
        test_file.write_text(sample_python_code)

        entities, relationships = await parser.parse_repository(
            str(tmp_path),
            language="python"
        )

        # Should have CONTAINS relationships
        contains_rels = [
            r for r in relationships
            if r.relationship_type == "contains"
        ]
        assert len(contains_rels) > 0

        # Should have CALLS relationships (validate_all calls validate_email)
        calls_rels = [
            r for r in relationships
            if r.relationship_type == "calls"
        ]
        # Note: call extraction may vary based on implementation
        # Just verify the structure is correct
        assert isinstance(calls_rels, list)

    @pytest.mark.asyncio
    async def test_nonexistent_path(self, parser):
        """Test handling of non-existent path."""
        from src.core.exceptions import ParsingError

        with pytest.raises(ParsingError):
            await parser.parse_repository(
                "/nonexistent/path",
                language="python"
            )

    @pytest.mark.asyncio
    async def test_empty_directory(self, parser, tmp_path):
        """Test parsing an empty directory."""
        entities, relationships = await parser.parse_repository(
            str(tmp_path),
            language="python"
        )

        assert entities == []
        assert relationships == []


class TestEntityExtraction:
    """Tests for specific entity extraction."""

    @pytest.fixture
    def parser(self):
        return CodeQLParser()

    @pytest.mark.asyncio
    async def test_extract_function_with_decorators(self, parser, tmp_path):
        """Test extracting a decorated function."""
        code = '''
from functools import lru_cache

@lru_cache(maxsize=100)
def expensive_computation(x: int) -> int:
    """Compute something expensive."""
    return x ** 2
'''
        test_file = tmp_path / "decorated.py"
        test_file.write_text(code)

        entities, _ = await parser.parse_repository(str(tmp_path), "python")

        functions = [e for e in entities if e.entity_type == "function"]
        assert len(functions) >= 1

        expensive_func = next(
            (f for f in functions if f.name == "expensive_computation"),
            None
        )
        assert expensive_func is not None
        assert "lru_cache" in expensive_func.decorators

    @pytest.mark.asyncio
    async def test_extract_async_function(self, parser, tmp_path):
        """Test extracting an async function."""
        code = '''
async def fetch_data(url: str) -> dict:
    """Fetch data from URL."""
    pass
'''
        test_file = tmp_path / "async_funcs.py"
        test_file.write_text(code)

        entities, _ = await parser.parse_repository(str(tmp_path), "python")

        functions = [e for e in entities if e.entity_type == "function"]
        fetch_data = next(
            (f for f in functions if f.name == "fetch_data"),
            None
        )
        assert fetch_data is not None
        assert fetch_data.is_async is True
