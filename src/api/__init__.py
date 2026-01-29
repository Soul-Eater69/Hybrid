"""
API Module
==========

Contains FastAPI routers and endpoint definitions.

Routers:
    - health: Health check endpoints
    - repositories: Repository analysis endpoints
    - search: Code search endpoints
    - impact: Impact analysis endpoints
    - generate: Code generation endpoints
"""

from src.api.router import api_router

__all__ = ["api_router"]
