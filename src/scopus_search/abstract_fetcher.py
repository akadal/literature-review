"""Helpers for enriching Scopus records with abstracts and OA metadata."""

from __future__ import annotations

import re
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover - exercised only in minimal environments.
    requests = None  # type: ignore[assignment]

from .utils import setup_logging

logger = setup_logging(verbose=False)


class AbstractFetcher:
    """Fetch article abstracts by DOI from public metadata providers."""

    def __init__(self, timeout: int = 20) -> None:
        if requests is None:
            raise RuntimeError(
                "The 'requests' package is required for abstract fetching. "
                "Install the project with `pip install -e .`."
            )
        self.timeout = timeout
        self.session = requests.Session()

    def fetch(self, doi: str) -> tuple[str, dict[str, Any]]:
        """Return ``(abstract, metadata)`` for a DOI when any provider has it."""

        if not doi:
            return "", {}

        for provider in (self._semantic_scholar, self._openalex, self._crossref):
            abstract, metadata = provider(doi)
            if abstract:
                return abstract, metadata

        return "", {}

    def _semantic_scholar(self, doi: str) -> tuple[str, dict[str, Any]]:
        url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=abstract,openAccessPdf"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.debug("Semantic Scholar abstract fetch failed for %s: %s", doi, exc)
            return "", {}

        metadata: dict[str, Any] = {}
        pdf = data.get("openAccessPdf") or {}
        if isinstance(pdf, dict):
            metadata["pdf_url"] = pdf.get("url", "")

        return data.get("abstract", "") or "", metadata

    def _openalex(self, doi: str) -> tuple[str, dict[str, Any]]:
        url = f"https://api.openalex.org/works/doi:{doi}"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.debug("OpenAlex abstract fetch failed for %s: %s", doi, exc)
            return "", {}

        metadata: dict[str, Any] = {}
        location = data.get("best_oa_location") or {}
        if isinstance(location, dict):
            metadata["pdf_url"] = location.get("pdf_url", "") or location.get("landing_page_url", "")

        return self._decode_openalex_abstract(data), metadata

    def _crossref(self, doi: str) -> tuple[str, dict[str, Any]]:
        url = f"https://api.crossref.org/works/{doi}"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json().get("message", {})
        except Exception as exc:
            logger.debug("Crossref abstract fetch failed for %s: %s", doi, exc)
            return "", {}

        return self._strip_xml_tags(data.get("abstract", "") or ""), {}

    def _decode_openalex_abstract(self, data: dict[str, Any]) -> str:
        inverted = data.get("abstract_inverted_index") or {}
        if not isinstance(inverted, dict) or not inverted:
            return ""

        positions = [
            position
            for word_positions in inverted.values()
            if isinstance(word_positions, list)
            for position in word_positions
            if isinstance(position, int)
        ]
        if not positions:
            return ""

        words = [""] * (max(positions) + 1)
        for word, word_positions in inverted.items():
            if not isinstance(word_positions, list):
                continue
            for position in word_positions:
                if isinstance(position, int):
                    words[position] = str(word)

        return " ".join(word for word in words if word).strip()

    def _strip_xml_tags(self, text: str) -> str:
        text = re.sub(r"<[^>]+>", "", text)
        return text.replace("\n", " ").strip()
