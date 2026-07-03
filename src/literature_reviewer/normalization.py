"""Normalize and cross-check article records from WoS and Scopus."""

from __future__ import annotations

import re
from collections.abc import Iterable
from difflib import SequenceMatcher
from hashlib import sha1
from typing import Any, Optional

from .models import EvidenceGroup, UnifiedArticle


def normalize_doi(doi: object) -> str:
    text = str(doi or "").strip().lower()
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text)
    text = re.sub(r"^doi:\s*", "", text)
    return text.rstrip(".")


def normalize_title(title: object) -> str:
    text = str(title or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def title_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, normalize_title(left), normalize_title(right)).ratio()


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _as_dict(record: Any) -> dict[str, Any]:
    if hasattr(record, "to_dict"):
        return dict(record.to_dict())
    if isinstance(record, dict):
        return dict(record)
    raise TypeError(f"Unsupported article record type: {type(record)!r}")


def _split_keywords(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").split(";") if item.strip()]


def article_from_record(record: Any, source: Optional[str] = None) -> UnifiedArticle:
    data = _as_dict(record)
    guessed_source = source or ("scopus" if "EID" in data else "wos")
    guessed_source = guessed_source.lower()

    if guessed_source == "wos":
        return UnifiedArticle(
            source="wos",
            source_id=str(data.get("UID", "") or data.get("Source_ID", "")),
            title=str(data.get("Title", "") or ""),
            authors=str(data.get("Authors", "") or ""),
            journal=str(data.get("Journal", "") or ""),
            year=_safe_int(data.get("Year")),
            doi=normalize_doi(data.get("DOI")),
            citations=_safe_int(data.get("Times_Cited", data.get("Citations", 0))),
            abstract=str(data.get("Abstract", "") or ""),
            keywords=_split_keywords(data.get("Keywords", "")),
            document_type=str(data.get("Document_Type", "") or ""),
            open_access=bool(data.get("Open_Access", False)),
            pdf_url=str(data.get("PDF_URL", "") or ""),
            pdf_path=str(data.get("PDF_Path", "") or ""),
            raw=data,
        )

    if guessed_source == "scopus":
        return UnifiedArticle(
            source="scopus",
            source_id=str(data.get("EID", "") or data.get("Source_ID", "")),
            title=str(data.get("Title", "") or ""),
            authors=str(data.get("Authors", "") or ""),
            journal=str(data.get("Journal", "") or ""),
            year=_safe_int(data.get("Year")),
            doi=normalize_doi(data.get("DOI")),
            citations=_safe_int(data.get("CitedBy_Count", data.get("Citations", 0))),
            abstract=str(data.get("Abstract", "") or ""),
            keywords=_split_keywords(data.get("Keywords", "")),
            document_type=str(data.get("Document_Type", "") or ""),
            open_access=bool(data.get("Open_Access", False)),
            pdf_url=str(data.get("PDF_URL", "") or ""),
            pdf_path=str(data.get("PDF_Path", "") or ""),
            raw=data,
        )

    raise ValueError(f"Unsupported source: {source}")


def normalize_records(
    wos_records: Optional[Iterable[Any]] = None,
    scopus_records: Optional[Iterable[Any]] = None,
) -> list[UnifiedArticle]:
    articles: list[UnifiedArticle] = []
    for record in wos_records or []:
        articles.append(article_from_record(record, "wos"))
    for record in scopus_records or []:
        articles.append(article_from_record(record, "scopus"))
    return articles


def _same_year_or_unknown(left: int, right: int) -> bool:
    return not left or not right or abs(left - right) <= 1


def _group_key_for(article: UnifiedArticle) -> str:
    if article.doi:
        return f"doi:{article.doi}"
    digest = sha1(normalize_title(article.title).encode("utf-8")).hexdigest()[:12]
    return f"title:{digest}"


def group_articles(
    articles: Iterable[UnifiedArticle],
    title_threshold: float = 0.92,
) -> list[EvidenceGroup]:
    groups: list[EvidenceGroup] = []

    for article in articles:
        target: Optional[EvidenceGroup] = None
        if article.doi:
            for group in groups:
                if group.doi and group.doi == article.doi:
                    target = group
                    break

        if target is None and article.title:
            for group in groups:
                if not _same_year_or_unknown(group.year, article.year):
                    continue
                if title_similarity(group.canonical_title, article.title) >= title_threshold:
                    target = group
                    break

        if target is None:
            target = EvidenceGroup(group_key=_group_key_for(article))
            groups.append(target)

        target.articles.append(article)

    for group in groups:
        group.confidence = _confidence_for_group(group)
        group.warnings = _warnings_for_group(group)

    return sorted(groups, key=lambda group: (-len(group.source_names), -group.confidence, group.canonical_title))


def _confidence_for_group(group: EvidenceGroup) -> float:
    if group.doi and len(group.source_names) > 1:
        return 1.0
    if len(group.source_names) > 1:
        return 0.9
    if group.doi:
        return 0.75
    return 0.55


def _warnings_for_group(group: EvidenceGroup) -> list[str]:
    warnings: list[str] = []
    years = sorted({article.year for article in group.articles if article.year})
    if len(years) > 1 and years[-1] - years[0] > 1:
        warnings.append(f"Conflicting publication years: {years}")
    dois = sorted({article.doi for article in group.articles if article.doi})
    if len(dois) > 1:
        warnings.append(f"Conflicting DOIs: {dois}")
    if len(group.source_names) == 1:
        warnings.append("Observed in one source only; treat as unconfirmed by the other index.")
    if not group.doi:
        warnings.append("No DOI available; deduplication used title/year similarity.")
    return warnings
