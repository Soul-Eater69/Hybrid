"""
Core Module
===========

Contains configuration, logging setup, and core utilities used across the application.

Components:
    - config: Application settings loaded from environment variables
    - logging: Structured logging configuration
    - exceptions: Custom exception classes
"""

from src.core.config import settings
from src.core.logging import get_logger

__all__ = ["settings", "get_logger"]
