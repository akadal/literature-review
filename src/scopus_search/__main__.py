"""Command-line interface for Scopus Search."""

from __future__ import annotations

import argparse

from .client import ScopusAPIError
from .researcher import ScopusResearcher


def main() -> None:
    parser = argparse.ArgumentParser(prog="scopus-search", description="Run a Scopus literature search.")
    parser.add_argument("query", help="Scopus advanced search query")
    parser.add_argument("--year-range", default=None, help="Year or inclusive range, for example 2020-2025")
    parser.add_argument("--doc-type", default="Article OR Review", help="Article, Review, or raw Scopus filter")
    parser.add_argument("--max-results", type=int, default=25)
    parser.add_argument("--sort-field", default="relevancy")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--api-key", default=None, help="Elsevier API key. Defaults to SCOPUS_API_KEY.")
    parser.add_argument("--insttoken", default=None, help="Optional Elsevier institution token.")
    parser.add_argument("--no-abstract", action="store_true", help="Skip DOI-based abstract enrichment.")
    parser.add_argument("--download-pdfs", action="store_true", help="Download open-access PDFs when found.")
    parser.add_argument("--quiet", action="store_true", help="Use less verbose logging.")
    args = parser.parse_args()

    try:
        researcher = ScopusResearcher(
            api_key=args.api_key,
            insttoken=args.insttoken,
            verbose=not args.quiet,
        )
        researcher.search(
            query=args.query,
            year_range=args.year_range,
            doc_type=args.doc_type,
            max_results=args.max_results,
            fetch_abstract=not args.no_abstract,
            download_pdfs=args.download_pdfs,
            output_dir=args.output_dir,
            sort_field=args.sort_field,
        )
    except ScopusAPIError as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
