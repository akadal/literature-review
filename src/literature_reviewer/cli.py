"""Command-line interface for the literature reviewer."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

from dotenv import load_dotenv

from .models import ReviewRequest
from .queries import build_scopus_query, build_wos_query
from .reviewer import LiteratureReviewer


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return doctor(check_apis=args.check_apis)
    if args.command == "search":
        return search(args)
    if args.command == "review-files":
        return review_files(args)

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="literature-review")
    subparsers = parser.add_subparsers(dest="command")

    search_parser = subparsers.add_parser("search", help="Run WoS and/or Scopus searches.")
    add_request_args(search_parser)
    search_parser.add_argument("--sources", default="wos,scopus", help="Comma-separated: wos,scopus")
    search_parser.add_argument("--no-abstract", action="store_true", help="Skip DOI abstract enrichment.")
    search_parser.add_argument("--download-pdfs", action="store_true", help="Download legal open-access PDFs.")

    files_parser = subparsers.add_parser("review-files", help="Create a review from existing CSV/JSON exports.")
    add_request_args(files_parser)
    files_parser.add_argument("paths", nargs="+", help="WoS/Scopus CSV or JSON export paths.")

    doctor_parser = subparsers.add_parser("doctor", help="Check local setup without printing secrets.")
    doctor_parser.add_argument("--check-apis", action="store_true", help="Make one tiny live request per configured API.")

    return parser


def add_request_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--topic", default="", help="Plain topic used to build both provider queries.")
    parser.add_argument("--wos-query", default="", help="Raw WoS Advanced Search query.")
    parser.add_argument("--scopus-query", default="", help="Raw Scopus advanced query.")
    parser.add_argument("--year-range", default=None, help="Year or inclusive range, for example 2020-2026.")
    parser.add_argument("--doc-type", default="Article OR Review")
    parser.add_argument("--max-results", type=int, default=50, help="Max records per source.")
    parser.add_argument("--output-dir", default="output/literature_review")


def _request_from_args(args: argparse.Namespace) -> ReviewRequest:
    sources = tuple(part.strip().lower() for part in getattr(args, "sources", "wos,scopus").split(",") if part.strip())
    return ReviewRequest(
        topic=args.topic,
        wos_query=args.wos_query,
        scopus_query=args.scopus_query,
        year_range=args.year_range,
        doc_type=args.doc_type,
        max_results_per_source=args.max_results,
        sources=sources,
        fetch_abstracts=not getattr(args, "no_abstract", False),
        download_pdfs=getattr(args, "download_pdfs", False),
        output_dir=args.output_dir,
    )


def search(args: argparse.Namespace) -> int:
    request = _request_from_args(args)
    result = LiteratureReviewer().search(request)
    print(f"Review written to: {result.output_paths['review_markdown']}")
    print(f"Evidence groups: {result.diagnostics['evidence_groups']}")
    print(f"Cross-source groups: {result.diagnostics['cross_source_groups']}")
    return 0


def review_files(args: argparse.Namespace) -> int:
    request = _request_from_args(args)
    result = LiteratureReviewer().from_export_files(request, args.paths)
    print(f"Review written to: {result.output_paths['review_markdown']}")
    print(f"Evidence groups: {result.diagnostics['evidence_groups']}")
    return 0


def doctor(check_apis: bool = False) -> int:
    load_dotenv()
    checks = {
        "WOS_API_KEY": bool(os.getenv("WOS_API_KEY")),
        "SCOPUS_API_KEY": bool(os.getenv("SCOPUS_API_KEY")),
        "SCOPUS_INSTTOKEN": bool(os.getenv("SCOPUS_INSTTOKEN")),
        "UNPAYWALL_EMAIL": bool(os.getenv("UNPAYWALL_EMAIL")),
    }
    for name, present in checks.items():
        print(f"{name}: {'present' if present else 'missing'}")

    print(f"Example WoS query: {build_wos_query('blockchain tourism')}")
    print(f"Example Scopus query: {build_scopus_query('blockchain tourism')}")

    if not check_apis:
        return 0

    failures: list[str] = []
    try:
        from wos_search import WosClient

        WosClient().search(query='TS=("blockchain")', editions="WOS+SCI,WOS+SSCI", page=1, limit=1)
        print("WoS live check: ok")
    except Exception as exc:  # pragma: no cover - depends on external credentials/network.
        failures.append(f"WoS live check failed: {exc}")

    try:
        from scopus_search import ScopusClient

        ScopusClient().search(query='TITLE-ABS-KEY("blockchain")', start=0, count=1)
        print("Scopus live check: ok")
    except Exception as exc:  # pragma: no cover - depends on external credentials/network.
        failures.append(f"Scopus live check failed: {exc}")

    for failure in failures:
        print(failure, file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
