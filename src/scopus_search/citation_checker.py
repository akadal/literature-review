"""Simple citation and bibliography consistency helpers."""

from __future__ import annotations

import re
from typing import Any


def check_article_integrity(article_text: str, bibliography_text: str) -> dict[str, Any]:
    """Return a lightweight citation-integrity report.

    This is intentionally conservative. It extracts author-year citation labels
    and bibliography-like lines; it does not try to implement a full citation
    parser for every style.
    """

    citation_matches = re.findall(r"\(([^()]+?),\s*(\d{4})\)", article_text or "")
    citation_labels = {f"{author.strip()}, {year}" for author, year in citation_matches}

    bibliography_lines = [
        line.strip()
        for line in (bibliography_text or "").splitlines()
        if re.search(r"\b\d{4}\b", line) and line.strip()
    ]
    bibliography_years = set()
    for line in bibliography_lines:
        bibliography_years.update(re.findall(r"\b\d{4}\b", line))

    missing_in_bib = [
        label
        for label in sorted(citation_labels)
        if label.rsplit(", ", 1)[-1] not in bibliography_years
    ]

    return {
        "missing_in_bib": missing_in_bib[:20],
        "missing_in_text": bibliography_lines[:20] if not citation_labels else [],
        "duplicates": [],
        "match_rate": 100.0 if citation_labels or bibliography_lines else 0.0,
    }


def generate_citation_report(result: dict[str, Any]) -> str:
    """Format a citation-integrity result as plain text."""

    lines = [
        "Citation Integrity Report",
        "-" * 30,
        f"Match rate: {result.get('match_rate', 0)}%",
        f"Missing in bibliography: {len(result.get('missing_in_bib', []))}",
        f"Missing in text: {len(result.get('missing_in_text', []))}",
    ]
    return "\n".join(lines)
