"""
Logging Module
==============

Configures structured logging using structlog for the entire application.
Provides consistent, JSON-formatted logs that are easy to parse and analyze.

HOW IT WORKS:
    1. Uses structlog for structured logging (key-value pairs)
    2. In development: Pretty-printed, colored console output
    3. In production: JSON-formatted for log aggregation systems

USAGE:
    from src.core.logging import get_logger

    # Create a logger for your module
    logger = get_logger(__name__)

    # Log with context
    logger.info("Processing file", filename="app.py", lines=100)
    logger.error("Failed to connect", service="neo4j", error=str(e))

DATA FLOW:
    Your code calls logger.info/error/etc
            ↓
    structlog processes the log entry
            ↓
    Processors add timestamp, log level, etc
            ↓
    Rendered as pretty text (dev) or JSON (prod)
            ↓
    Output to console (stdout/stderr)
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from src.core.config import settings


def setup_logging() -> None:
    """
    Configure structured logging for the application.

    This function sets up structlog with appropriate processors
    based on the environment (development vs production).

    Call this once at application startup (in main.py).
    """
    # -------------------------------------------------------------------------
    # Shared Processors (used in all environments)
    # -------------------------------------------------------------------------
    # Processors are functions that transform log entries
    shared_processors: list[Processor] = [
        # Add log level (INFO, ERROR, etc) to the event dict
        structlog.stdlib.add_log_level,
        # Add logger name to identify source module
        structlog.stdlib.add_logger_name,
        # Add timestamp in ISO format
        structlog.processors.TimeStamper(fmt="iso"),
        # Handle exceptions - format tracebacks nicely
        structlog.processors.StackInfoRenderer(),
        # Format exception info if present
        structlog.processors.format_exc_info,
        # Decode unicode properly
        structlog.processors.UnicodeDecoder(),
    ]

    # -------------------------------------------------------------------------
    # Environment-specific Configuration
    # -------------------------------------------------------------------------
    if settings.is_debug:
        # Development: Pretty, colored console output
        processors = shared_processors + [
            # Pretty print with colors for terminal
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        # Production: JSON format for log aggregation
        processors = shared_processors + [
            # Render as JSON for easy parsing
            structlog.processors.JSONRenderer()
        ]

    # -------------------------------------------------------------------------
    # Configure structlog
    # -------------------------------------------------------------------------
    structlog.configure(
        processors=processors,
        # Use standard library logger as base
        wrapper_class=structlog.stdlib.BoundLogger,
        # Use dict for context (faster than OrderedDict)
        context_class=dict,
        # Get logger from standard library
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache logger on first use
        cache_logger_on_first_use=True,
    )

    # -------------------------------------------------------------------------
    # Configure Standard Library Logging
    # -------------------------------------------------------------------------
    # This ensures third-party libraries also use our format
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name, typically __name__ of the calling module.
              If None, returns a logger without a name.

    Returns:
        A bound structlog logger that can be used for logging.

    Example:
        logger = get_logger(__name__)
        logger.info("Starting process", step=1, total=10)

        # Output (dev):
        # 2024-01-29 10:30:45 [info] Starting process  step=1 total=10

        # Output (prod):
        # {"timestamp":"2024-01-29T10:30:45","level":"info","event":"Starting process","step":1,"total":10}
    """
    return structlog.get_logger(name)


class LoggerMixin:
    """
    Mixin class that provides a logger attribute to any class.

    Usage:
        class MyService(LoggerMixin):
            def do_something(self):
                self.logger.info("Doing something")

    The logger name will be automatically set to the class's module path.
    """

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger named after this class's module."""
        return get_logger(self.__class__.__module__)
