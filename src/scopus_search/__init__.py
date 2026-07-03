"""Scopus Search package."""

from .client import ScopusAPIError, ScopusClient
from .models import ScopusArticle, SearchConfig
from .researcher import ScopusResearcher

__all__ = [
    "ScopusAPIError",
    "ScopusClient",
    "ScopusArticle",
    "SearchConfig",
    "ScopusResearcher",
]

__version__ = "0.1.0"
