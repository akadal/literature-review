"""High-level orchestration for Scopus literature searches."""

from __future__ import annotations

import os
import time
from typing import Optional

from .abstract_fetcher import AbstractFetcher
from .client import ScopusAPIError, ScopusClient
from .config import CSV_COLUMNS, SCOPUS_PAGE_SIZE
from .models import ScopusArticle, SearchConfig
from .pdf_downloader import PDFDownloader
from .utils import (
    build_summary_report,
    ensure_dir,
    export_to_csv,
    export_to_json,
    extract_query_label,
    generate_run_id,
    setup_logging,
)

logger = setup_logging(verbose=False)


class ScopusResearcher:
    """Coordinate search, optional abstract enrichment, optional PDF download, and export."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        insttoken: Optional[str] = None,
        verbose: bool = True,
    ) -> None:
        self.client = ScopusClient(api_key=api_key, insttoken=insttoken)
        self.fetcher = AbstractFetcher()
        self.downloader: Optional[PDFDownloader] = None
        self.verbose = verbose

        if verbose:
            logger.setLevel("DEBUG")

    def search(
        self,
        query: str,
        year_range: Optional[str] = None,
        doc_type: str = "Article OR Review",
        max_results: int = 100,
        fetch_abstract: bool = True,
        download_pdfs: bool = False,
        output_dir: str = "output",
        sort_field: str = "relevancy",
    ) -> list[ScopusArticle]:
        """Run a Scopus search and export the resulting article records."""

        config = SearchConfig(
            query=query,
            year_range=year_range,
            doc_type=doc_type,
            max_results=max_results,
            sort_field=sort_field,
            fetch_abstract=fetch_abstract,
            download_pdfs=download_pdfs,
            output_dir=output_dir,
        )

        if download_pdfs:
            self.downloader = PDFDownloader(pdf_dir=os.path.join(output_dir, "pdfs"))

        start_time = time.time()
        articles: list[ScopusArticle] = []
        start = 0
        full_query = config.build_full_query()

        logger.info("=" * 60)
        logger.info("STARTING SCOPUS LITERATURE SEARCH")
        logger.info("=" * 60)
        logger.info("Query       : %s", config.query)
        logger.info("Full query  : %s", full_query)
        logger.info("Document type: %s", config.doc_type)
        logger.info("Year range  : %s", config.year_range)
        logger.info("Target      : %s", config.max_results)
        logger.info("=" * 60)

        while len(articles) < config.max_results:
            count = min(SCOPUS_PAGE_SIZE, config.max_results - len(articles))

            try:
                data = self.client.search(
                    query=full_query,
                    start=start,
                    count=count,
                    sort=config.sort_field,
                )
            except ScopusAPIError as exc:
                logger.error("Scopus API error: %s", exc)
                break

            results = data.get("search-results", {})
            entries = results.get("entry", []) or []

            if start == 0:
                total_records = self._safe_int(results.get("opensearch:totalResults", 0))
                logger.info("Scopus returned %s matching records.", total_records)
                if not entries:
                    logger.info("No matching records found.")
                    break

            if not entries:
                logger.info("No more records found.")
                break

            for entry in entries:
                if not isinstance(entry, dict):
                    continue

                article = ScopusArticle.from_scopus_entry(entry)

                if fetch_abstract and article.doi:
                    abstract, metadata = self.fetcher.fetch(article.doi)
                    if abstract:
                        article.abstract = abstract
                    if metadata.get("pdf_url"):
                        article.pdf_url = str(metadata["pdf_url"])
                        article.open_access = True

                if download_pdfs and article.doi and self.downloader:
                    pdf_path = self.downloader.download(
                        doi=article.doi,
                        title=article.title,
                        provided_pdf_url=article.pdf_url,
                    )
                    article.pdf_path = pdf_path or ""

                articles.append(article)
                logger.info(
                    "[%s/%s] %s... | citations: %s | abstract: %s | PDF: %s",
                    len(articles),
                    config.max_results,
                    article.title[:60],
                    article.citedby_count,
                    "yes" if article.abstract else "no",
                    "yes" if article.pdf_path else "no",
                )

                if len(articles) >= config.max_results:
                    break

            start += count
            if len(entries) < count:
                break

        elapsed = time.time() - start_time
        logger.info("")
        logger.info("-" * 60)
        logger.info("Search complete. Processed %s articles.", len(articles))
        logger.info("Elapsed time: %.1f seconds", elapsed)
        logger.info("Scopus API requests: %s", self.client.total_requests)

        if self.downloader:
            logger.info(
                "PDF downloads: %s succeeded, %s failed",
                self.downloader.downloaded,
                self.downloader.failed,
            )

        self._export_results(articles, config, elapsed)
        return articles

    def _export_results(self, articles: list[ScopusArticle], config: SearchConfig, elapsed: float = 0.0) -> None:
        if not articles:
            logger.warning("No data to save.")
            return

        label = extract_query_label(config.query)
        run_id = generate_run_id()
        ensure_dir(config.output_dir)

        data = [article.to_dict() for article in articles]
        csv_path = os.path.join(config.output_dir, f"{label}_{run_id}.csv")
        json_path = os.path.join(config.output_dir, f"{label}_{run_id}.json")
        report_path = os.path.join(config.output_dir, f"{label}_{run_id}_report.txt")

        export_to_csv(data, csv_path, columns=CSV_COLUMNS)
        export_to_json(data, json_path)

        report = build_summary_report(data, config.query, config.year_range or "", elapsed)
        with open(report_path, "w", encoding="utf-8") as file:
            file.write(report)

        logger.info("CSV saved: %s", csv_path)
        logger.info("JSON saved: %s", json_path)
        logger.info("Report saved: %s", report_path)
        print("\n" + report)

    @staticmethod
    def _safe_int(value: object, default: int = 0) -> int:
        try:
            return int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default
