"""Varsayılan ayarlar ve sabitler."""

from typing import Dict, Any

# WoS Starter API
WOS_BASE_URL = "https://api.clarivate.com/apis/wos-starter/v1"
WOS_RATE_LIMIT_RPS = 5
WOS_PAGE_SIZE = 50

# Varsayılan indeksler: SCI-Expanded (SCI-E) + SSCI
# NOT: ESCI (Emerging Sources Citation Index) varsayılan olarak dahil DEĞİLDİR.
DEFAULT_EDITIONS = "WOS+SCI,WOS+SSCI"

# İzin verilen indeksler
# SCI kodu WoS API'de SCI-Expanded (SCI-E) anlamına gelir.
ALLOWED_EDITIONS = [
    "WOS+SCI",   # SCI-Expanded (SCI-E)
    "WOS+SSCI",
    "WOS+AHCI",
    "WOS+ESCI",  # Emerging Sources - varsayılan olarak kullanılmaz
    "WOS+CCR",
    "WOS+IC",
    "WOS+ISSHP",
    "WOS+ISTP",
    "WOS+BHCI",
    "WOS+BSCI",
]

# Doküman türleri
DEFAULT_DOC_TYPE = "Article OR Review"
ALLOWED_DOC_TYPES = [
    "Article OR Review",
    "Article",
    "Review",
    "Editorial Material",
    "Letter",
    "Book Chapter",
    "",
]

# Abstract sağlayıcı URL'leri
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=abstract,openAccessPdf"
CROSSREF_API = "https://api.crossref.org/works/{doi}"
OPENALEX_API = "https://api.openalex.org/works/doi:{doi}"

# PDF indirme
UNPAYWALL_API = "https://api.unpaywall.org/v2/{doi}?email={email}"

# İstek başlıkları
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "WoS-Search-Skill/2.0 (Academic Research Tool)",
}

# CSV sütunları
CSV_COLUMNS = [
    "UID",
    "Title",
    "Authors",
    "Journal",
    "Year",
    "DOI",
    "Times_Cited",
    "Abstract",
    "Keywords",
    "Document_Type",
    "Editions",
    "Volume",
    "Issue",
    "Pages",
    "Publisher",
    "Language",
    "References_Count",
    "Open_Access",
    "PDF_URL",
    "PDF_Path",
    "Fetched_At",
]

# Kalite kontrol sabitleri
MIN_ABSTRACT_LENGTH = 50
MIN_TITLE_LENGTH = 5


def get_default_config() -> Dict[str, Any]:
    """Varsayılan konfigürasyon sözlüğü döndür."""
    return {
        "editions": DEFAULT_EDITIONS,
        "doc_type": DEFAULT_DOC_TYPE,
        "max_results": 100,
        "sort_field": "RS+D",
        "fetch_abstract": True,
        "download_pdfs": False,
        "output_dir": "output",
        "pdf_dir": "output/pdfs",
        "verbose": True,
        "retry_attempts": 3,
        "request_timeout": 30,
    }
