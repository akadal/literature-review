"""Core data models for grounded review workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

VALID_SOURCES = {"wos", "scopus"}


@dataclass(frozen=True)
class ReviewRequest:
    """Configuration for one literature-review run."""

    topic: str = ""
    wos_query: str = ""
    scopus_query: str = ""
    year_range: Optional[str] = None
    doc_type: str = "Article OR Review"
    max_results_per_source: int = 50
    sources: tuple[str, ...] = ("wos", "scopus")
    fetch_abstracts: bool = True
    download_pdfs: bool = False
    output_dir: str = "output/literature_review"
    wos_sort_field: str = "RS+D"
    scopus_sort_field: str = "relevancy"

    def __post_init__(self) -> None:
        if self.max_results_per_source < 1:
            raise ValueError("max_results_per_source must be at least 1.")
        if not (self.topic or self.wos_query or self.scopus_query):
            raise ValueError("Provide a topic, wos_query, or scopus_query.")
        invalid_sources = set(self.sources) - VALID_SOURCES
        if invalid_sources:
            raise ValueError(f"Unsupported sources: {sorted(invalid_sources)}")


@dataclass
class UnifiedArticle:
    """Source-neutral article record used by the cross-check layer."""

    source: str
    source_id: str
    title: str
    authors: str = ""
    journal: str = ""
    year: int = 0
    doi: str = ""
    citations: int = 0
    abstract: str = ""
    keywords: list[str] = field(default_factory=list)
    document_type: str = ""
    open_access: bool = False
    pdf_url: str = ""
    pdf_path: str = ""
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def evidence_id(self) -> str:
        base = self.source_id or self.doi or self.title
        return f"{self.source.upper()}:{base}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "Evidence_ID": self.evidence_id,
            "Source": self.source,
            "Source_ID": self.source_id,
            "Title": self.title,
            "Authors": self.authors,
            "Journal": self.journal,
            "Year": self.year,
            "DOI": self.doi,
            "Citations": self.citations,
            "Abstract": self.abstract,
            "Keywords": "; ".join(self.keywords),
            "Document_Type": self.document_type,
            "Open_Access": self.open_access,
            "PDF_URL": self.pdf_url,
            "PDF_Path": self.pdf_path,
        }


@dataclass
class EvidenceGroup:
    """A deduplicated article-level evidence group."""

    group_key: str
    articles: list[UnifiedArticle] = field(default_factory=list)
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def doi(self) -> str:
        for article in self.articles:
            if article.doi:
                return article.doi
        return ""

    @property
    def canonical_title(self) -> str:
        titles = [article.title for article in self.articles if article.title]
        return max(titles, key=len) if titles else ""

    @property
    def source_names(self) -> list[str]:
        return sorted({article.source for article in self.articles})

    @property
    def evidence_ids(self) -> list[str]:
        return [article.evidence_id for article in self.articles]

    @property
    def year(self) -> int:
        years = [article.year for article in self.articles if article.year]
        return max(set(years), key=years.count) if years else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "Group_Key": self.group_key,
            "Canonical_Title": self.canonical_title,
            "DOI": self.doi,
            "Year": self.year,
            "Sources": self.source_names,
            "Evidence_IDs": self.evidence_ids,
            "Confidence": self.confidence,
            "Warnings": self.warnings,
            "Articles": [article.to_dict() for article in self.articles],
        }


@dataclass
class ReviewResult:
    """Completed review result with exports and diagnostics."""

    request: ReviewRequest
    articles: list[UnifiedArticle]
    evidence_groups: list[EvidenceGroup]
    diagnostics: dict[str, Any]
    output_paths: dict[str, str] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "request": {
                "topic": self.request.topic,
                "wos_query": self.request.wos_query,
                "scopus_query": self.request.scopus_query,
                "year_range": self.request.year_range,
                "doc_type": self.request.doc_type,
                "max_results_per_source": self.request.max_results_per_source,
                "sources": list(self.request.sources),
                "fetch_abstracts": self.request.fetch_abstracts,
                "download_pdfs": self.request.download_pdfs,
            },
            "diagnostics": self.diagnostics,
            "output_paths": self.output_paths,
            "evidence_groups": [group.to_dict() for group in self.evidence_groups],
        }
