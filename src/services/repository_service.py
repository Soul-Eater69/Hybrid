"""
Repository Service
==================

Manages repository operations: cloning, loading, and tracking.
This is the entry point for processing new codebases.

HOW IT WORKS:
    1. User provides a GitHub URL or local path
    2. If remote: Clone the repository
    3. Detect the programming language
    4. Parse code using CodeQL/AST
    5. Store entities in Neo4j and Vector DB
    6. Track repository status

DATA FLOW:
    GitHub URL / Local Path
           ↓
    RepositoryService.analyze()
           ↓
    ┌──────────────────────────────────────┐
    │ If remote URL:                        │
    │   └── git clone → local directory     │
    └──────────────────────────────────────┘
           ↓
    Language Detection
           ↓
    CodeQLParser.parse_repository()
           ↓
    ┌────────────────────────────────────────┐
    │ Store in parallel:                     │
    │   ├── Neo4jService.store_entities()   │
    │   └── VectorService.store_entities()  │
    └────────────────────────────────────────┘
           ↓
    Repository marked as READY

REPOSITORY STATES:
    PENDING → CLONING → ANALYZING → INDEXING → READY
                                         ↓
                                      FAILED (on error)

USAGE:
    from src.services.repository_service import RepositoryService

    repo_svc = RepositoryService(neo4j, vector_svc, parser)

    # Analyze a GitHub repository
    repo = await repo_svc.analyze(
        url="https://github.com/fastapi/fastapi",
        branch="main"
    )

    # Check status
    status = await repo_svc.get_status(repo.id)
"""

import asyncio
import os
import shutil
from pathlib import Path
from typing import Any
from uuid import UUID

import git
from git import Repo
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import settings
from src.core.exceptions import (
    InvalidRepositoryURLError,
    RepositoryCloneError,
    RepositoryNotFoundError,
)
from src.core.logging import LoggerMixin
from src.models.repository import Repository, RepositoryStatus, RepositoryLanguage
from src.services.codeql_parser import CodeQLParser
from src.services.neo4j_service import Neo4jService
from src.services.vector_service import VectorService


class RepositoryService(LoggerMixin):
    """
    Service for managing repository analysis.

    Coordinates cloning, parsing, and indexing of code repositories.

    Attributes:
        neo4j: Neo4j service for graph storage
        vector: Vector service for embeddings
        parser: CodeQL parser for code analysis
        repos_dir: Directory for cloned repositories
        repositories: In-memory repository tracking (would use DB in prod)
    """

    def __init__(
        self,
        neo4j: Neo4jService,
        vector: VectorService,
        parser: CodeQLParser
    ) -> None:
        """
        Initialize the repository service.

        Args:
            neo4j: Neo4j service instance
            vector: Vector service instance
            parser: CodeQL parser instance
        """
        self.neo4j = neo4j
        self.vector = vector
        self.parser = parser
        self.repos_dir = Path(settings.repos_dir)

        # In-memory storage (replace with DB in production)
        self._repositories: dict[str, Repository] = {}

    async def analyze(
        self,
        url: str | None = None,
        local_path: str | None = None,
        branch: str = "main",
        language: str | None = None,
        force_reanalyze: bool = False
    ) -> Repository:
        """
        Analyze a repository and index its code.

        This is the main entry point for repository processing.

        Args:
            url: GitHub/GitLab repository URL (optional if local_path)
            local_path: Path to local repository (optional if url)
            branch: Branch to analyze
            language: Programming language (auto-detected if not specified)
            force_reanalyze: Re-analyze even if already indexed

        Returns:
            Repository object with status and metadata

        Raises:
            InvalidRepositoryURLError: If URL is malformed
            RepositoryNotFoundError: If repository doesn't exist
            RepositoryCloneError: If cloning fails

        Example:
            # Analyze a GitHub repo
            repo = await repo_svc.analyze(
                url="https://github.com/user/project"
            )

            # Analyze a local repo
            repo = await repo_svc.analyze(
                local_path="/path/to/project"
            )
        """
        if not url and not local_path:
            raise ValueError("Either 'url' or 'local_path' must be provided")

        # Create repository record
        if url:
            repo = Repository.from_github_url(url)
            repo.branch = branch
        else:
            repo = Repository(
                name=Path(local_path).name,
                local_path=local_path,
                branch=branch
            )

        # Check if already analyzed
        if not force_reanalyze and await self._is_already_indexed(repo):
            self.logger.info(
                "Repository already indexed",
                name=repo.name,
                id=str(repo.id)
            )
            return self._repositories[str(repo.id)]

        # Store repository record
        self._repositories[str(repo.id)] = repo

        self.logger.info(
            "Starting repository analysis",
            name=repo.name,
            url=url,
            local_path=local_path
        )

        try:
            # Clone if remote
            if url:
                repo.status = RepositoryStatus.CLONING
                repo.local_path = await self._clone_repository(url, branch)

            # Detect language if not specified
            if not language:
                language = await self._detect_language(repo.local_path)
            repo.language = RepositoryLanguage(language)

            # Parse code
            repo.status = RepositoryStatus.ANALYZING
            entities, relationships = await self.parser.parse_repository(
                repo.local_path,
                language
            )

            self.logger.info(
                "Parsing complete",
                entities=len(entities),
                relationships=len(relationships)
            )

            # Index in parallel
            repo.status = RepositoryStatus.INDEXING
            await asyncio.gather(
                self.neo4j.store_entities(entities, str(repo.id)),
                self.neo4j.store_relationships(relationships, str(repo.id)),
                self.vector.store_entities(entities, str(repo.id))
            )

            # Mark as ready
            repo.mark_ready(
                entity_count=len(entities),
                relationship_count=len(relationships)
            )

            self.logger.info(
                "Repository analysis complete",
                name=repo.name,
                id=str(repo.id),
                status=repo.status
            )

            return repo

        except Exception as e:
            self.logger.error(
                "Repository analysis failed",
                name=repo.name,
                error=str(e)
            )
            repo.mark_failed(str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30)
    )
    async def _clone_repository(
        self,
        url: str,
        branch: str = "main"
    ) -> str:
        """
        Clone a remote repository.

        Args:
            url: Repository URL
            branch: Branch to clone

        Returns:
            Path to cloned repository

        Raises:
            RepositoryCloneError: If cloning fails
        """
        # Validate URL
        if not url.startswith(("https://", "git@")):
            raise InvalidRepositoryURLError(url)

        # Determine clone directory
        repo_name = url.rstrip("/").rstrip(".git").split("/")[-1]
        clone_path = self.repos_dir / f"{repo_name}_{branch}"

        # Remove existing clone
        if clone_path.exists():
            shutil.rmtree(clone_path)

        self.logger.info(
            "Cloning repository",
            url=url,
            branch=branch,
            path=str(clone_path)
        )

        try:
            # Clone with depth=1 for faster cloning
            env = {}
            if settings.github_token:
                # Use token for authentication
                if url.startswith("https://github.com"):
                    url = url.replace(
                        "https://github.com",
                        f"https://{settings.github_token}@github.com"
                    )

            await asyncio.to_thread(
                git.Repo.clone_from,
                url,
                clone_path,
                branch=branch,
                depth=1,
                env=env
            )

            self.logger.info("Clone complete", path=str(clone_path))
            return str(clone_path)

        except git.GitCommandError as e:
            self.logger.error("Clone failed", error=str(e))
            raise RepositoryCloneError(url, str(e))

    async def _detect_language(self, repo_path: str) -> str:
        """
        Detect the primary programming language of a repository.

        Uses file extension analysis to determine the language.

        Args:
            repo_path: Path to repository

        Returns:
            Detected language string
        """
        path = Path(repo_path)
        extension_counts: dict[str, int] = {}

        # Map extensions to languages
        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".c": "cpp",
            ".h": "cpp",
            ".cs": "csharp",
            ".rb": "ruby",
        }

        # Count files by extension
        for ext, lang in extension_map.items():
            count = len(list(path.rglob(f"*{ext}")))
            if lang in extension_counts:
                extension_counts[lang] += count
            else:
                extension_counts[lang] = count

        # Return most common language
        if extension_counts:
            return max(extension_counts, key=extension_counts.get)

        return "python"  # Default fallback

    async def _is_already_indexed(self, repo: Repository) -> bool:
        """
        Check if a repository has already been indexed.

        Args:
            repo: Repository to check

        Returns:
            True if already indexed
        """
        # Check in-memory cache
        for existing in self._repositories.values():
            if existing.url == repo.url and existing.is_ready:
                return True
            if (existing.local_path == repo.local_path and
                    existing.is_ready):
                return True
        return False

    async def get_repository(self, repository_id: str) -> Repository | None:
        """
        Get a repository by ID.

        Args:
            repository_id: UUID of the repository

        Returns:
            Repository object or None
        """
        return self._repositories.get(repository_id)

    async def get_status(self, repository_id: str) -> dict[str, Any]:
        """
        Get the current status of a repository.

        Args:
            repository_id: UUID of the repository

        Returns:
            Status dict with details
        """
        repo = self._repositories.get(repository_id)
        if not repo:
            return {"status": "not_found", "message": "Repository not found"}

        result = {
            "id": str(repo.id),
            "name": repo.name,
            "status": repo.status,
            "entity_count": repo.entity_count,
            "relationship_count": repo.relationship_count,
        }

        if repo.status == RepositoryStatus.FAILED:
            result["error"] = repo.error_message

        if repo.completed_at:
            result["completed_at"] = repo.completed_at.isoformat()

        return result

    async def list_repositories(self) -> list[dict[str, Any]]:
        """
        List all tracked repositories.

        Returns:
            List of repository summaries
        """
        return [
            {
                "id": str(repo.id),
                "name": repo.name,
                "url": repo.url,
                "status": repo.status,
                "language": repo.language,
                "entity_count": repo.entity_count,
                "created_at": repo.created_at.isoformat()
            }
            for repo in self._repositories.values()
        ]

    async def delete_repository(self, repository_id: str) -> bool:
        """
        Delete a repository and all its indexed data.

        Args:
            repository_id: UUID of the repository

        Returns:
            True if deleted, False if not found
        """
        repo = self._repositories.get(repository_id)
        if not repo:
            return False

        self.logger.info(
            "Deleting repository",
            id=repository_id,
            name=repo.name
        )

        # Delete from storages
        await asyncio.gather(
            self.neo4j.delete_repository(repository_id),
            self.vector.delete_repository(repository_id)
        )

        # Delete local clone if exists
        if repo.local_path and repo.url:  # Only delete if it was cloned
            clone_path = Path(repo.local_path)
            if clone_path.exists():
                shutil.rmtree(clone_path)

        # Remove from tracking
        del self._repositories[repository_id]

        self.logger.info("Repository deleted", id=repository_id)
        return True
