"""High-level reviewer that combines WoS, Scopus, and evidence guardrails."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Optional

from .exports import export_review
from .models import EvidenceGroup, ReviewRequest, ReviewResult, UnifiedArticle
from .normalization import article_from_record, group_articles, normalize_records
from .queries import build_scopus_query, build_wos_query


class LiteratureReviewer:
    """Run or assemble a source-grounded literature review."""

    def search(self, request: ReviewRequest) -> ReviewResult:
        wos_records: list[Any] = []
        scopus_records: list[Any] = []
        wos_query = request.wos_query or (build_wos_query(request.topic) if request.topic else "")
        scopus_query = request.scopus_query or (build_scopus_query(request.topic) if request.topic else "")

        if "wos" in request.sources:
            wos_records = self._search_wos(request, wos_query)
        if "scopus" in request.sources:
            scopus_records = self._search_scopus(request, scopus_query)

        return self.from_records(
            request=request,
            wos_records=wos_records,
            scopus_records=scopus_records,
            extra_diagnostics={"wos_query": wos_query, "scopus_query": scopus_query},
        )

    def from_records(
        self,
        request: ReviewRequest,
        wos_records: Optional[Iterable[Any]] = None,
        scopus_records: Optional[Iterable[Any]] = None,
        extra_diagnostics: Optional[dict[str, Any]] = None,
    ) -> ReviewResult:
        articles = normalize_records(wos_records=wos_records, scopus_records=scopus_records)
        groups = group_articles(articles)
        diagnostics = self._diagnostics(articles, groups)
        diagnostics.update(extra_diagnostics or {})
        result = ReviewResult(
            request=request,
            articles=articles,
            evidence_groups=groups,
            diagnostics=diagnostics,
        )
        result.output_paths = export_review(result, request.output_dir)
        return result

    def from_export_files(
        self,
        request: ReviewRequest,
        paths: Iterable[str],
    ) -> ReviewResult:
        wos_records: list[dict[str, Any]] = []
        scopus_records: list[dict[str, Any]] = []
        for path in paths:
            records = self._load_records(path)
            for record in records:
                article = article_from_record(record)
                if article.source == "wos":
                    wos_records.append(record)
                else:
                    scopus_records.append(record)
        return self.from_records(request=request, wos_records=wos_records, scopus_records=scopus_records)

    def _search_wos(self, request: ReviewRequest, query: str) -> list[Any]:
        from wos_search import WosResearcher

        researcher = WosResearcher(verbose=True)
        return researcher.search(
            query=query,
            year_range=request.year_range,
            doc_type=request.doc_type,
            max_results=request.max_results_per_source,
            fetch_abstract=request.fetch_abstracts,
            download_pdfs=request.download_pdfs,
            output_dir=str(Path(request.output_dir) / "wos"),
            sort_field=request.wos_sort_field,
        )

    def _search_scopus(self, request: ReviewRequest, query: str) -> list[Any]:
        from scopus_search import ScopusResearcher

        researcher = ScopusResearcher(verbose=True)
        return researcher.search(
            query=query,
            year_range=request.year_range,
            doc_type=request.doc_type,
            max_results=request.max_results_per_source,
            fetch_abstract=request.fetch_abstracts,
            download_pdfs=request.download_pdfs,
            output_dir=str(Path(request.output_dir) / "scopus"),
            sort_field=request.scopus_sort_field,
        )

    @staticmethod
    def _load_records(path: str) -> list[dict[str, Any]]:
        input_path = Path(path)
        if input_path.suffix.lower() == ".json":
            data = json.loads(input_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [dict(item) for item in data if isinstance(item, dict)]
            if isinstance(data, dict) and isinstance(data.get("Articles"), list):
                return [dict(item) for item in data["Articles"] if isinstance(item, dict)]
            return []

        if input_path.suffix.lower() == ".csv":
            with input_path.open("r", encoding="utf-8-sig", newline="") as file:
                return [dict(row) for row in csv.DictReader(file)]

        raise ValueError(f"Unsupported export file type: {path}")

    @staticmethod
    def _diagnostics(articles: list[UnifiedArticle], groups: list[EvidenceGroup]) -> dict[str, Any]:
        warnings = [warning for group in groups for warning in group.warnings]
        return {
            "source_records": len(articles),
            "evidence_groups": len(groups),
            "cross_source_groups": sum(1 for group in groups if len(group.source_names) > 1),
            "missing_doi_records": sum(1 for article in articles if not article.doi),
            "missing_abstract_records": sum(1 for article in articles if not article.abstract),
            "sources_present": sorted({article.source for article in articles}),
            "warnings": warnings,
        }
