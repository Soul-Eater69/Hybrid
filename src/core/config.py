"""
Configuration Module
====================

This module handles all application configuration using Pydantic Settings.
Configuration is loaded from environment variables or .env file.

HOW IT WORKS:
    1. Pydantic Settings automatically reads from environment variables
    2. Variable names in .env should match the field names (case-insensitive)
    3. The `settings` object is a singleton - import it anywhere you need config

USAGE:
    from src.core.config import settings

    # Access any setting
    print(settings.openai_api_key)
    print(settings.neo4j_uri)

DATA FLOW:
    .env file / Environment Variables
           ↓
    Pydantic Settings (validation & typing)
           ↓
    `settings` singleton object
           ↓
    Used by services throughout the app
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings

    All configuration values for the Code Intelligence Backend.
    Values are loaded from environment variables or .env file.

    Attributes:
        app_name: Name of the application (for logging/identification)
        app_env: Environment (development/staging/production)
        debug: Enable debug mode (more verbose logging)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

        api_host: Host to bind the API server
        api_port: Port for the API server
        api_workers: Number of worker processes

        openai_api_key: Your OpenAI API key for LLM operations
        openai_model: The GPT model to use for code generation
        openai_embedding_model: Model for creating embeddings

        neo4j_uri: Connection URI for Neo4j database
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password

        chroma_persist_directory: Where to store ChromaDB data
        chroma_collection_name: Name of the embeddings collection

        codeql_path: Path to CodeQL CLI binary
        codeql_database_path: Where to store CodeQL databases

        github_token: GitHub Personal Access Token for repo access

        temp_dir: Temporary files directory
        repos_dir: Cloned repositories directory
    """

    # -------------------------------------------------------------------------
    # Application Settings
    # -------------------------------------------------------------------------
    app_name: str = Field(
        default="code-intel-backend",
        description="Application name for logging and identification"
    )
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Current environment"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging verbosity level"
    )

    # -------------------------------------------------------------------------
    # API Server Settings
    # -------------------------------------------------------------------------
    api_host: str = Field(
        default="0.0.0.0",
        description="Host to bind the API server"
    )
    api_port: int = Field(
        default=8000,
        description="Port for the API server"
    )
    api_workers: int = Field(
        default=4,
        description="Number of worker processes"
    )

    # -------------------------------------------------------------------------
    # OpenAI / LLM Settings
    # -------------------------------------------------------------------------
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for LLM operations"
    )
    openai_model: str = Field(
        default="gpt-4-turbo-preview",
        description="GPT model for code generation"
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Model for creating embeddings"
    )

    # -------------------------------------------------------------------------
    # Neo4j Knowledge Graph Settings
    # -------------------------------------------------------------------------
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI"
    )
    neo4j_user: str = Field(
        default="neo4j",
        description="Neo4j username"
    )
    neo4j_password: str = Field(
        default="",
        description="Neo4j password"
    )

    # -------------------------------------------------------------------------
    # ChromaDB Vector Database Settings
    # -------------------------------------------------------------------------
    chroma_persist_directory: str = Field(
        default="./data/chroma",
        description="Directory to persist ChromaDB data"
    )
    chroma_collection_name: str = Field(
        default="code_embeddings",
        description="Name of the ChromaDB collection"
    )

    # -------------------------------------------------------------------------
    # CodeQL Settings
    # -------------------------------------------------------------------------
    codeql_path: str = Field(
        default="/usr/local/bin/codeql",
        description="Path to CodeQL CLI binary"
    )
    codeql_database_path: str = Field(
        default="./data/codeql_dbs",
        description="Directory for CodeQL databases"
    )

    # -------------------------------------------------------------------------
    # GitHub Settings
    # -------------------------------------------------------------------------
    github_token: str = Field(
        default="",
        description="GitHub Personal Access Token"
    )

    # -------------------------------------------------------------------------
    # Azure Cosmos DB Settings (for chat conversations)
    # -------------------------------------------------------------------------
    cosmos_endpoint: str = Field(
        default="",
        description="Azure Cosmos DB endpoint URL"
    )
    cosmos_key: str = Field(
        default="",
        description="Azure Cosmos DB access key"
    )
    cosmos_database: str = Field(
        default="code_intel",
        description="Cosmos DB database name"
    )
    cosmos_container: str = Field(
        default="conversations",
        description="Cosmos DB container name for conversations"
    )

    # -------------------------------------------------------------------------
    # Directory Settings
    # -------------------------------------------------------------------------
    temp_dir: str = Field(
        default="./temp",
        description="Temporary files directory"
    )
    repos_dir: str = Field(
        default="./repos",
        description="Cloned repositories directory"
    )

    # -------------------------------------------------------------------------
    # Pydantic Settings Configuration
    # -------------------------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------
    @field_validator("chroma_persist_directory", "codeql_database_path", "temp_dir", "repos_dir")
    @classmethod
    def create_directories(cls, v: str) -> str:
        """Ensure directories exist when settings are loaded."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path.absolute())

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"

    @property
    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.debug and not self.is_production


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    This is more efficient than creating a new Settings object each time.

    Returns:
        Settings: The application settings singleton
    """
    return Settings()


# Create a global settings instance for easy import
settings = get_settings()
