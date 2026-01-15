"""API v1 module"""
from app.api.v1.router import api_router
from app.api.v1.query import router as query_router
from app.api.v1.system import router as system_router
from app.api.v1.documents import router as documents_router
from app.api.v1.graph import router as graph_router

__all__ = [
    "api_router",
    "query_router",
    "system_router",
    "documents_router",
    "graph_router",
]
