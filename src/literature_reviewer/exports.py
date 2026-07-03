"""Export review artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import ReviewResult
from .report import build_markdown_report

ARTICLE_COLUMNS = [
    "Evidence_ID",
    "Source",
    "Source_ID",
    "Title",
    "Authors",
    "Journal",
    "Year",
    "DOI",
    "Citations",
    "Abstract",
    "Keywords",
    "Document_Type",
    "Open_Access",
    "PDF_URL",
    "PDF_Path",
]


def export_review(result: ReviewResult, output_dir: str) -> dict[str, str]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    article_path = target / "articles.csv"
    with article_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=ARTICLE_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(article.to_dict() for article in result.articles)

    groups_path = target / "evidence_groups.json"
    with groups_path.open("w", encoding="utf-8") as file:
        json.dump([group.to_dict() for group in result.evidence_groups], file, ensure_ascii=False, indent=2)

    diagnostics_path = target / "diagnostics.json"
    with diagnostics_path.open("w", encoding="utf-8") as file:
        json.dump(result.to_dict(), file, ensure_ascii=False, indent=2)

    report_path = target / "review.md"
    report_path.write_text(build_markdown_report(result), encoding="utf-8")

    return {
        "articles_csv": str(article_path),
        "evidence_groups_json": str(groups_path),
        "diagnostics_json": str(diagnostics_path),
        "review_markdown": str(report_path),
    }
