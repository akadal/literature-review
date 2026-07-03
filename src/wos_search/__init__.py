"""WoS Search Skill - Web of Science sistematik literatür taraması."""

from .researcher import WosResearcher
from .client import WosClient, WosAPIError
from .models import WosArticle, SearchConfig
from .abstract_fetcher import AbstractFetcher
from .pdf_downloader import PDFDownloader
from .citation_checker import (
    CitationCheckResult,
    check_article_integrity,
    generate_citation_report,
)
from .utils import (
    setup_logging,
    export_to_csv,
    export_to_json,
    build_summary_report,
)

__version__ = "2.0.0"
__all__ = [
    "WosResearcher",
    "WosClient",
    "WosAPIError",
    "WosArticle",
    "SearchConfig",
    "AbstractFetcher",
    "PDFDownloader",
    "CitationCheckResult",
    "check_article_integrity",
    "generate_citation_report",
    "setup_logging",
    "export_to_csv",
    "export_to_json",
    "build_summary_report",
]
