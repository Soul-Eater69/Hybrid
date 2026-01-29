"""
Repository Model
================

Defines models for repository tracking and management.

HOW IT WORKS:
    1. User provides a repository URL or local path
    2. System clones/loads the repository
    3. Repository object tracks analysis state
    4. Multiple analyses can be run on the same repository

REPOSITORY STATES:
    - PENDING: Repository queued for processing
    - CLONING: Currently being cloned from remote
    - ANALYZING: CodeQL and parsing in progress
    - INDEXING: Building vector embeddings and graph
    - READY: Analysis complete, ready for queries
    - FAILED: An error occurred during processing

DATA FLOW:
    User Input (URL/path)
           ↓
    Clone Repository (if remote)
           ↓
    CodeQL Database Creation
           ↓
    Parse & Extract Entities
           ↓
    Index to Neo4j & Vector DB
           ↓
    Repository Status: READY

USAGE:
    from src.models.repository import Repository, RepositoryStatus

    # Create a repository record
    repo = Repository(
        url="https://github.com/user/project",
        name="project",
        language="python"
    )
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class RepositoryStatus(str, Enum):
    """
    Status states for repository processing.

    Tracks the current state of repository analysis.
    """

    PENDING = "pending"        # Queued for processing
    CLONING = "cloning"        # Being cloned from remote
    ANALYZING = "analyzing"    # CodeQL analysis in progress
    INDEXING = "indexing"      # Building embeddings and graph
    READY = "ready"            # Analysis complete
    FAILED = "failed"          # Error occurred
    UPDATING = "updating"      # Updating existing analysis


class RepositoryLanguage(str, Enum):
    """
    Supported programming languages.

    CodeQL and our parsers support these languages.
    """

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    CPP = "cpp"
    CSHARP = "csharp"
    RUBY = "ruby"


class Repository(BaseModel):
    """
    Represents a repository being analyzed.

    Tracks the state and metadata of a repository
    throughout the analysis pipeline.

    Attributes:
        id: Unique identifier for this repository record
        url: Remote URL of the repository (GitHub, GitLab, etc.)
        name: Repository name
        owner: Repository owner (user or organization)
        local_path: Path where the repository is stored locally
        language: Primary programming language
        branch: Branch being analyzed
        commit_hash: Specific commit being analyzed
        status: Current processing status
        entity_count: Number of code entities found
        relationship_count: Number of relationships found
        error_message: Error details if status is FAILED
        metadata: Additional repository metadata
        created_at: When analysis was started
        updated_at: When analysis was last updated
        completed_at: When analysis completed
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier"
    )
    url: str | None = Field(
        default=None,
        description="Remote repository URL"
    )
    name: str = Field(
        description="Repository name"
    )
    owner: str | None = Field(
        default=None,
        description="Repository owner"
    )
    local_path: str | None = Field(
        default=None,
        description="Local filesystem path"
    )
    language: RepositoryLanguage = Field(
        default=RepositoryLanguage.PYTHON,
        description="Primary programming language"
    )
    branch: str = Field(
        default="main",
        description="Branch being analyzed"
    )
    commit_hash: str | None = Field(
        default=None,
        description="Specific commit hash"
    )
    status: RepositoryStatus = Field(
        default=RepositoryStatus.PENDING,
        description="Current processing status"
    )
    entity_count: int = Field(
        default=0,
        ge=0,
        description="Number of entities found"
    )
    relationship_count: int = Field(
        default=0,
        ge=0,
        description="Number of relationships found"
    )
    error_message: str | None = Field(
        default=None,
        description="Error details if failed"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When analysis started"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update time"
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When analysis completed"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True

    @property
    def is_remote(self) -> bool:
        """Check if this is a remote repository (needs cloning)."""
        return self.url is not None

    @property
    def is_ready(self) -> bool:
        """Check if repository is ready for queries."""
        return self.status == RepositoryStatus.READY

    @property
    def is_processing(self) -> bool:
        """Check if repository is currently being processed."""
        return self.status in [
            RepositoryStatus.PENDING,
            RepositoryStatus.CLONING,
            RepositoryStatus.ANALYZING,
            RepositoryStatus.INDEXING,
            RepositoryStatus.UPDATING,
        ]

    @classmethod
    def from_github_url(cls, url: str) -> "Repository":
        """
        Create a Repository from a GitHub URL.

        Parses the URL to extract owner and repository name.

        Args:
            url: GitHub repository URL

        Returns:
            Repository instance

        Example:
            repo = Repository.from_github_url(
                "https://github.com/owner/project"
            )
            # repo.owner = "owner"
            # repo.name = "project"
        """
        # Parse GitHub URL: https://github.com/owner/repo
        parts = url.rstrip("/").rstrip(".git").split("/")
        if len(parts) >= 2:
            owner = parts[-2]
            name = parts[-1]
        else:
            owner = None
            name = parts[-1] if parts else "unknown"

        return cls(
            url=url,
            name=name,
            owner=owner,
        )

    def mark_failed(self, error: str) -> None:
        """
        Mark repository as failed with error message.

        Args:
            error: Error message describing the failure
        """
        self.status = RepositoryStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.utcnow()

    def mark_ready(self, entity_count: int, relationship_count: int) -> None:
        """
        Mark repository as ready after successful analysis.

        Args:
            entity_count: Number of entities found
            relationship_count: Number of relationships found
        """
        self.status = RepositoryStatus.READY
        self.entity_count = entity_count
        self.relationship_count = relationship_count
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class AnalysisRequest(BaseModel):
    """
    Request to analyze a repository.

    Sent by the API to trigger repository analysis.

    Attributes:
        url: Remote repository URL (optional if local_path provided)
        local_path: Local filesystem path (optional if url provided)
        branch: Branch to analyze
        language: Programming language (auto-detected if not specified)
        force_reanalyze: If True, re-analyze even if already indexed
    """

    url: str | None = Field(
        default=None,
        description="Remote repository URL"
    )
    local_path: str | None = Field(
        default=None,
        description="Local filesystem path"
    )
    branch: str = Field(
        default="main",
        description="Branch to analyze"
    )
    language: RepositoryLanguage | None = Field(
        default=None,
        description="Programming language (auto-detected if not provided)"
    )
    force_reanalyze: bool = Field(
        default=False,
        description="Force re-analysis even if already indexed"
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate that either url or local_path is provided."""
        if not self.url and not self.local_path:
            raise ValueError("Either 'url' or 'local_path' must be provided")
