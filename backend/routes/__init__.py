"""API routes for the Multimodal Event Explorer."""

from .search import router as search_router
from .events import router as events_router
from .domains import router as domains_router
from .images import router as images_router
from .stats import router as stats_router

__all__ = [
    "search_router",
    "events_router", 
    "domains_router",
    "images_router",
    "stats_router",
]
