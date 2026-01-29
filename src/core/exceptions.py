"""
Exceptions Module
=================

Custom exception classes for the Code Intelligence Backend.
Using specific exceptions makes error handling cleaner and more informative.

HOW IT WORKS:
    1. All custom exceptions inherit from CodeIntelError (base class)
    2. Each exception has a specific error code for identification
    3. Exceptions carry context data for detailed error messages
    4. FastAPI handlers convert these to appropriate HTTP responses

USAGE:
    from src.core.exceptions import RepositoryNotFoundError, CodeQLError

    # Raise specific exceptions
    raise RepositoryNotFoundError("https://github.com/user/repo")

    # Handle exceptions
    try:
        analyze_code()
    except CodeIntelError as e:
        logger.error(e.message, code=e.code, details=e.details)

EXCEPTION HIERARCHY:
    CodeIntelError (base)
    ├── RepositoryError
    │   ├── RepositoryNotFoundError
    │   ├── RepositoryCloneError
    │   └── InvalidRepositoryURLError
    ├── AnalysisError
    │   ├── CodeQLError
    │   └── ParsingError
    ├── StorageError
    │   ├── Neo4jError
    │   └── VectorDBError
    └── GenerationError
        └── LLMError
"""

from typing import Any


class CodeIntelError(Exception):
    """
    Base exception for all Code Intelligence errors.

    All custom exceptions should inherit from this class.
    Provides consistent structure for error handling.

    Attributes:
        message: Human-readable error message
        code: Unique error code for identification
        details: Additional context about the error
    """

    def __init__(
        self,
        message: str,
        code: str = "CODE_INTEL_ERROR",
        details: dict[str, Any] | None = None
    ) -> None:
        """
        Initialize the exception.

        Args:
            message: Human-readable description of the error
            code: Unique error code (e.g., "REPO_NOT_FOUND")
            details: Additional context as key-value pairs
        """
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert exception to dictionary for JSON responses.

        Returns:
            Dictionary with error information
        """
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


# =============================================================================
# REPOSITORY ERRORS
# =============================================================================

class RepositoryError(CodeIntelError):
    """Base class for repository-related errors."""

    def __init__(
        self,
        message: str,
        code: str = "REPOSITORY_ERROR",
        details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message, code, details)


class RepositoryNotFoundError(RepositoryError):
    """
    Raised when a repository cannot be found.

    Example:
        raise RepositoryNotFoundError("https://github.com/user/nonexistent")
    """

    def __init__(self, repo_url: str) -> None:
        super().__init__(
            message=f"Repository not found: {repo_url}",
            code="REPOSITORY_NOT_FOUND",
            details={"repository_url": repo_url}
        )


class RepositoryCloneError(RepositoryError):
    """
    Raised when repository cloning fails.

    Example:
        raise RepositoryCloneError(
            "https://github.com/user/repo",
            "Authentication failed"
        )
    """

    def __init__(self, repo_url: str, reason: str) -> None:
        super().__init__(
            message=f"Failed to clone repository: {reason}",
            code="REPOSITORY_CLONE_ERROR",
            details={"repository_url": repo_url, "reason": reason}
        )


class InvalidRepositoryURLError(RepositoryError):
    """
    Raised when a repository URL is malformed.

    Example:
        raise InvalidRepositoryURLError("not-a-valid-url")
    """

    def __init__(self, repo_url: str) -> None:
        super().__init__(
            message=f"Invalid repository URL format: {repo_url}",
            code="INVALID_REPOSITORY_URL",
            details={"repository_url": repo_url}
        )


# =============================================================================
# ANALYSIS ERRORS
# =============================================================================

class AnalysisError(CodeIntelError):
    """Base class for code analysis errors."""

    def __init__(
        self,
        message: str,
        code: str = "ANALYSIS_ERROR",
        details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message, code, details)


class CodeQLError(AnalysisError):
    """
    Raised when CodeQL analysis fails.

    Example:
        raise CodeQLError(
            "Failed to create database",
            command="codeql database create",
            exit_code=1
        )
    """

    def __init__(
        self,
        message: str,
        command: str | None = None,
        exit_code: int | None = None
    ) -> None:
        details = {}
        if command:
            details["command"] = command
        if exit_code is not None:
            details["exit_code"] = exit_code
        super().__init__(
            message=f"CodeQL error: {message}",
            code="CODEQL_ERROR",
            details=details
        )


class ParsingError(AnalysisError):
    """
    Raised when code parsing fails.

    Example:
        raise ParsingError("app.py", "Syntax error at line 42")
    """

    def __init__(self, file_path: str, reason: str) -> None:
        super().__init__(
            message=f"Failed to parse {file_path}: {reason}",
            code="PARSING_ERROR",
            details={"file_path": file_path, "reason": reason}
        )


# =============================================================================
# STORAGE ERRORS
# =============================================================================

class StorageError(CodeIntelError):
    """Base class for storage-related errors."""

    def __init__(
        self,
        message: str,
        code: str = "STORAGE_ERROR",
        details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message, code, details)


class Neo4jError(StorageError):
    """
    Raised when Neo4j operations fail.

    Example:
        raise Neo4jError("Connection refused", query="MATCH (n) RETURN n")
    """

    def __init__(self, message: str, query: str | None = None) -> None:
        details = {}
        if query:
            details["query"] = query
        super().__init__(
            message=f"Neo4j error: {message}",
            code="NEO4J_ERROR",
            details=details
        )


class VectorDBError(StorageError):
    """
    Raised when vector database operations fail.

    Example:
        raise VectorDBError("Collection not found", collection="code_embeddings")
    """

    def __init__(self, message: str, collection: str | None = None) -> None:
        details = {}
        if collection:
            details["collection"] = collection
        super().__init__(
            message=f"Vector DB error: {message}",
            code="VECTOR_DB_ERROR",
            details=details
        )


# =============================================================================
# GENERATION ERRORS
# =============================================================================

class GenerationError(CodeIntelError):
    """Base class for code generation errors."""

    def __init__(
        self,
        message: str,
        code: str = "GENERATION_ERROR",
        details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message, code, details)


class LLMError(GenerationError):
    """
    Raised when LLM operations fail.

    Example:
        raise LLMError("Rate limit exceeded", model="gpt-4")
    """

    def __init__(self, message: str, model: str | None = None) -> None:
        details = {}
        if model:
            details["model"] = model
        super().__init__(
            message=f"LLM error: {message}",
            code="LLM_ERROR",
            details=details
        )
