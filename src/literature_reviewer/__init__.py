"""Grounded literature review orchestration for WoS and Scopus."""

from .guardrails import EvidenceGuard, UnsupportedClaimError
from .models import EvidenceGroup, ReviewRequest, ReviewResult, UnifiedArticle
from .normalization import group_articles, normalize_records
from .queries import build_scopus_query, build_wos_query
from .reviewer import LiteratureReviewer

__all__ = [
    "EvidenceGroup",
    "EvidenceGuard",
    "LiteratureReviewer",
    "ReviewRequest",
    "ReviewResult",
    "UnifiedArticle",
    "UnsupportedClaimError",
    "build_scopus_query",
    "build_wos_query",
    "group_articles",
    "normalize_records",
]

__version__ = "0.1.0"
