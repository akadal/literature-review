"""Default settings and constants for Scopus Search."""

from __future__ import annotations

from typing import Any

SCOPUS_BASE_URL = "https://api.elsevier.com/content"
SCOPUS_SEARCH_URL = f"{SCOPUS_BASE_URL}/search/scopus"
SCOPUS_RATE_LIMIT_RPS = 5
SCOPUS_PAGE_SIZE = 25

DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Scopus-Search/0.1 (Academic Research Tool)",
}

CSV_COLUMNS = [
    "EID",
    "Title",
    "Authors",
    "Journal",
    "Year",
    "DOI",
    "CitedBy_Count",
    "Abstract",
    "Keywords",
    "Document_Type",
    "Volume",
    "Issue",
    "Pages",
    "Affiliations",
    "Open_Access",
    "PDF_URL",
    "PDF_Path",
    "Fetched_At",
]


def get_default_config() -> dict[str, Any]:
    """Return default search settings used by the high-level researcher."""

    return {
        "year_range": None,
        "doc_type": "Article OR Review",
        "max_results": 100,
        "sort_field": "relevancy",
        "fetch_abstract": True,
        "download_pdfs": False,
        "output_dir": "output",
        "verbose": True,
        "retry_attempts": 3,
        "request_timeout": 30,
    }
