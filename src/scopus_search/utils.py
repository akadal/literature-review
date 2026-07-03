"""General utility functions for Scopus Search."""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Optional, Union

from .config import CSV_COLUMNS


def setup_logging(verbose: bool = True) -> logging.Logger:
    """Configure and return the package logger."""

    logger = logging.getLogger("scopus_search")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def sanitize_filename(text: str, max_length: int = 60) -> str:
    """Convert arbitrary text into a short filesystem-friendly name."""

    if not text:
        return "untitled"

    cleaned = text.lower().strip()
    cleaned = re.sub(r"[^\w\s-]", "", cleaned)
    cleaned = re.sub(r"[-\s]+", "_", cleaned)
    return cleaned[:max_length].strip("_") or "untitled"


def extract_query_label(query: str) -> str:
    """Create a stable label for output files from a Scopus query."""

    terms = re.findall(r'"([^"]+)"', query)
    if terms:
        return "_".join(sanitize_filename(term) for term in terms[:3])

    words = re.findall(r"[A-Za-z0-9]+", query)
    if words:
        return "_".join(words[:4])

    return "search"


def generate_run_id() -> str:
    """Return a short run identifier."""

    return hashlib.sha1(str(time.time()).encode("utf-8")).hexdigest()[:8]


def ensure_dir(path: Union[str, Path]) -> Path:
    """Create a directory if needed and return it as a Path."""

    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def export_to_csv(
    data: list[dict[str, Any]],
    filepath: Union[str, Path],
    columns: Optional[list[str]] = None,
) -> str:
    """Export article dictionaries to CSV."""

    if not data:
        raise ValueError("No data available to export to CSV.")

    output_path = Path(filepath)
    ensure_dir(output_path.parent)

    with output_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=columns or CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)

    return str(output_path)


def export_to_json(data: list[dict[str, Any]], filepath: Union[str, Path]) -> str:
    """Export article dictionaries to JSON."""

    output_path = Path(filepath)
    ensure_dir(output_path.parent)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    return str(output_path)


def sleep_with_backoff(attempt: int, base: float = 1.0, cap: float = 30.0) -> None:
    """Sleep using capped exponential backoff with jitter."""

    import random

    wait = min(base * (2**attempt) + random.uniform(0, 1), cap)
    time.sleep(wait)


def calculate_abstract_coverage(articles: list[dict[str, Any]]) -> float:
    """Return the percentage of records that include a meaningful abstract."""

    if not articles:
        return 0.0

    has_abstract = sum(
        1 for article in articles if article.get("Abstract") and len(article.get("Abstract", "")) > 50
    )
    return (has_abstract / len(articles)) * 100


def calculate_pdf_coverage(articles: list[dict[str, Any]]) -> float:
    """Return the percentage of records that have an existing PDF path."""

    if not articles:
        return 0.0

    has_pdf = sum(
        1
        for article in articles
        if article.get("PDF_Path") and os.path.exists(str(article.get("PDF_Path", "")))
    )
    return (has_pdf / len(articles)) * 100


def build_summary_report(
    articles: list[dict[str, Any]],
    query: str,
    year_range: str,
    elapsed_seconds: float,
) -> str:
    """Build a plain-text summary report for a completed search."""

    total = len(articles)
    abstract_coverage = calculate_abstract_coverage(articles)
    pdf_coverage = calculate_pdf_coverage(articles)

    year_distribution: dict[int, int] = {}
    for article in articles:
        year = article.get("Year", 0)
        if year:
            year_distribution[int(year)] = year_distribution.get(int(year), 0) + 1

    journal_counts: dict[str, int] = {}
    for article in articles:
        journal = str(article.get("Journal", "")).strip()
        if journal:
            journal_counts[journal] = journal_counts.get(journal, 0) + 1

    top_journals = dict(sorted(journal_counts.items(), key=lambda item: item[1], reverse=True)[:5])

    lines = [
        "=" * 60,
        "SCOPUS SEARCH SUMMARY REPORT",
        "=" * 60,
        f"Query              : {query}",
        f"Year range         : {year_range}",
        f"Total articles     : {total}",
        f"Elapsed time       : {elapsed_seconds:.1f} seconds",
        f"Abstract coverage  : {abstract_coverage:.1f}%",
        f"PDF coverage       : {pdf_coverage:.1f}%",
        "-" * 60,
        "Year distribution:",
    ]

    for year in sorted(year_distribution):
        lines.append(f"  {year}: {year_distribution[year]} articles")

    lines.extend(["-" * 60, "Top journals:"])
    for journal, count in top_journals.items():
        lines.append(f"  {journal}: {count} articles")

    lines.append("=" * 60)
    return "\n".join(lines)
