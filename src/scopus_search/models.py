"""Data models used by Scopus Search."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass
class ScopusArticle:
    """Normalized article record returned by a Scopus search."""

    eid: str = ""
    title: str = ""
    authors: str = ""
    journal: str = ""
    year: int = 0
    doi: str = ""
    citedby_count: int = 0
    abstract: str = ""
    keywords: list[str] = field(default_factory=list)
    document_type: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    affiliations: str = ""
    open_access: bool = False
    pdf_url: str = ""
    pdf_path: str = ""
    fetched_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Return a CSV/JSON-friendly representation."""

        return {
            "EID": self.eid,
            "Title": self.title,
            "Authors": self.authors,
            "Journal": self.journal,
            "Year": self.year,
            "DOI": self.doi,
            "CitedBy_Count": self.citedby_count,
            "Abstract": self.abstract,
            "Keywords": "; ".join(self.keywords),
            "Document_Type": self.document_type,
            "Volume": self.volume,
            "Issue": self.issue,
            "Pages": self.pages,
            "Affiliations": self.affiliations,
            "Open_Access": self.open_access,
            "PDF_URL": self.pdf_url,
            "PDF_Path": self.pdf_path,
            "Fetched_At": self.fetched_at.isoformat(),
        }

    @classmethod
    def from_scopus_entry(cls, entry: dict[str, Any]) -> "ScopusArticle":
        """Build an article model from one Scopus API search entry."""

        authors = _as_list(entry.get("author"))
        affiliations = _as_list(entry.get("affiliation"))
        keywords_value = entry.get("authkeywords", [])

        if isinstance(keywords_value, str):
            keywords = [keyword.strip() for keyword in keywords_value.split(";") if keyword.strip()]
        else:
            keywords = [str(keyword).strip() for keyword in _as_list(keywords_value) if str(keyword).strip()]

        author_names: list[str] = []
        for author in authors:
            if isinstance(author, dict):
                name = (
                    author.get("authname")
                    or author.get("ce:indexed-name")
                    or author.get("surname")
                    or ""
                )
                if name:
                    author_names.append(str(name))
            elif author:
                author_names.append(str(author))
        # STANDARD view omits the "author" list and only returns the first author as dc:creator.
        if not author_names and entry.get("dc:creator"):
            author_names.append(str(entry["dc:creator"]))

        affiliation_names: list[str] = []
        for affiliation in affiliations:
            if isinstance(affiliation, dict):
                name = (
                    affiliation.get("affilname")
                    or affiliation.get("afdispname")
                    or affiliation.get("affiliation")
                    or ""
                )
                if name:
                    affiliation_names.append(str(name))
            elif affiliation:
                affiliation_names.append(str(affiliation))

        cover_date = str(entry.get("prism:coverDate", ""))
        year = _safe_int(cover_date[:4]) if cover_date else 0
        open_access_value = entry.get("openaccess", False)
        open_access = open_access_value is True or str(open_access_value).lower() in {"1", "true", "yes"}

        return cls(
            eid=str(entry.get("eid", "") or ""),
            title=str(entry.get("dc:title", "") or ""),
            authors="; ".join(author_names),
            journal=str(entry.get("prism:publicationName", "") or ""),
            year=year,
            doi=str(entry.get("prism:doi", "") or ""),
            citedby_count=_safe_int(entry.get("citedby-count", 0)),
            abstract=str(entry.get("dc:description", "") or entry.get("abstract", "") or ""),
            keywords=keywords,
            document_type=str(
                entry.get("subtypeDescription", "") or entry.get("prism:aggregationType", "") or ""
            ),
            volume=str(entry.get("prism:volume", "") or ""),
            issue=str(entry.get("prism:issueIdentifier", "") or ""),
            pages=str(entry.get("prism:pageRange", "") or ""),
            affiliations="; ".join(affiliation_names),
            open_access=open_access,
        )


@dataclass
class SearchConfig:
    """Search options for the high-level Scopus researcher."""

    query: str = ""
    year_range: Optional[str] = None
    doc_type: str = "Article OR Review"
    max_results: int = 100
    sort_field: str = "relevancy"
    fetch_abstract: bool = True
    download_pdfs: bool = False
    output_dir: str = "output"
    verbose: bool = True
    retry_attempts: int = 3
    request_timeout: int = 30

    def __post_init__(self) -> None:
        if self.max_results < 1:
            raise ValueError("max_results must be at least 1.")

        if not self.year_range:
            current_year = datetime.now().year
            self.year_range = f"{current_year - 4}-{current_year}"

    def build_full_query(self) -> str:
        """Return the user query plus year and document-type filters."""

        filters: list[str] = []
        query = self.query.strip()

        if self.year_range:
            year_range = str(self.year_range).strip()
            if "-" in year_range:
                start, end = [part.strip() for part in year_range.split("-", 1)]
                if start.isdigit() and end.isdigit():
                    filters.append(f"PUBYEAR > {int(start) - 1} AND PUBYEAR < {int(end) + 1}")
            elif year_range.isdigit():
                filters.append(f"PUBYEAR = {year_range}")

        doc_type = (self.doc_type or "").strip().lower()
        if doc_type == "article or review":
            filters.append("(DOCTYPE(ar) OR DOCTYPE(re))")
        elif doc_type == "article":
            filters.append("DOCTYPE(ar)")
        elif doc_type == "review":
            filters.append("DOCTYPE(re)")
        elif self.doc_type:
            filters.append(self.doc_type)

        if query and filters:
            return f"({query}) AND " + " AND ".join(filters)
        if query:
            return query
        return " AND ".join(filters)
