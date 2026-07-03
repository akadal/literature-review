"""Veri modelleri ve yapıları."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class WosArticle:
    """Bir WoS makalesinin veri modeli."""
    uid: str = ""
    title: str = ""
    authors: str = ""
    journal: str = ""
    year: int = 0
    doi: str = ""
    times_cited: int = 0
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    source_type: str = ""
    document_type: str = ""
    editions: List[str] = field(default_factory=list)
    volume: str = ""
    issue: str = ""
    pages: str = ""
    publisher: str = ""
    language: str = ""
    funding_text: str = ""
    references_count: int = 0
    references: List[str] = field(default_factory=list)
    pdf_url: str = ""
    pdf_path: str = ""
    open_access: bool = False
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Sözlük temsiline dönüştür (CSV/JSON için)."""
        d = {
            "UID": self.uid,
            "Title": self.title,
            "Authors": self.authors,
            "Journal": self.journal,
            "Year": self.year,
            "DOI": self.doi,
            "Times_Cited": self.times_cited,
            "Abstract": self.abstract,
            "Keywords": "; ".join(self.keywords),
            "Document_Type": self.document_type,
            "Editions": "; ".join(self.editions),
            "Volume": self.volume,
            "Issue": self.issue,
            "Pages": self.pages,
            "Publisher": self.publisher,
            "Language": self.language,
            "References_Count": self.references_count,
            "Open_Access": self.open_access,
            "PDF_URL": self.pdf_url,
            "PDF_Path": self.pdf_path,
            "Fetched_At": self.fetched_at.isoformat(),
        }
        return d

    @classmethod
    def from_wos_hit(cls, hit: Dict[str, Any]) -> "WosArticle":
        """WoS API yanıtından WosArticle oluştur."""
        source = hit.get("source", {})
        identifiers = hit.get("identifiers", {})
        names = hit.get("names", {})
        authors_list = names.get("authors", [])

        article = cls()
        article.uid = hit.get("uid", "")
        article.title = hit.get("title", "")
        article.authors = "; ".join(
            [a.get("displayName", "") for a in authors_list]
        )
        article.journal = source.get("sourceTitle", "")
        article.year = source.get("publishYear", 0)
        article.doi = identifiers.get("doi", "")
        article.volume = source.get("volume", "")
        article.issue = source.get("issue", "")
        article.pages = source.get("pages", "")
        article.publisher = source.get("publishers", [{}])[0].get("publisher", "") if source.get("publishers") else ""
        article.language = hit.get("language", {}).get("name", "")
        article.document_type = hit.get("doctype", "")
        article.editions = hit.get("edition", [])
        article.keywords = [k.strip() for k in hit.get("keywords", {}).get("authorKeywords", [])]
        article.funding_text = hit.get("fundingText", "")
        article.references_count = hit.get("referencesCount", 0)

        # Atıf sayısı (WOS veritabanından)
        for c in hit.get("citations", []):
            if c.get("db") == "WOS":
                article.times_cited = c.get("count", 0)
                break

        return article


@dataclass
class SearchConfig:
    """Arama konfigürasyonu."""
    query: str = ""
    year_range: Optional[str] = None
    doc_type: str = "Article OR Review"
    editions: str = "WOS+SCI,WOS+SSCI"
    max_results: int = 100
    sort_field: str = "RS+D"  # Relevance descending
    fetch_abstract: bool = True
    download_pdfs: bool = False
    output_dir: str = "output"
    pdf_dir: str = "output/pdfs"
    verbose: bool = True
    retry_attempts: int = 3
    request_timeout: int = 30

    def __post_init__(self):
        # Varsayılan yıl aralığı: son 5 yıl
        if not self.year_range:
            current_year = datetime.now().year
            self.year_range = f"{current_year - 4}-{current_year}"

    def build_full_query(self) -> str:
        """WoS API için tam sorguyu oluştur."""
        full = f"({self.query}) AND PY=({self.year_range})"
        if self.doc_type:
            full += f" AND DT=({self.doc_type})"
        return full
