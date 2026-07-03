"""Open-access PDF download helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:  # pragma: no cover - exercised only in minimal environments.
    requests = None  # type: ignore[assignment]

from .utils import sanitize_filename, setup_logging

logger = setup_logging(verbose=False)


class PDFDownloader:
    """Download open-access PDFs from a known URL or Unpaywall lookup."""

    def __init__(self, pdf_dir: str = "output/pdfs", email: Optional[str] = None, timeout: int = 30) -> None:
        if requests is None:
            raise RuntimeError(
                "The 'requests' package is required for PDF downloads. "
                "Install the project with `pip install -e .`."
            )
        self.pdf_dir = Path(pdf_dir)
        self.email = email or os.getenv("UNPAYWALL_EMAIL")
        self.timeout = timeout
        self.session = requests.Session()
        self.downloaded = 0
        self.failed = 0
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

    def download(self, doi: str, title: str, provided_pdf_url: Optional[str] = None) -> Optional[str]:
        """Download a PDF and return the local path, or ``None`` on failure."""

        pdf_url = provided_pdf_url or self._lookup_unpaywall(doi)
        if not pdf_url:
            self.failed += 1
            return None

        filename = sanitize_filename(title or doi) + ".pdf"
        target = self.pdf_dir / filename

        try:
            response = self.session.get(pdf_url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            with target.open("wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)

            if self._looks_like_pdf(target):
                self.downloaded += 1
                return str(target)

            target.unlink(missing_ok=True)
            self.failed += 1
            return None
        except Exception as exc:
            logger.debug("PDF download failed for %s: %s", doi, exc)
            self.failed += 1
            return None

    def _lookup_unpaywall(self, doi: str) -> Optional[str]:
        if not doi or not self.email:
            return None

        url = f"https://api.unpaywall.org/v2/{doi}?email={self.email}"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.debug("Unpaywall lookup failed for %s: %s", doi, exc)
            return None

        best_location = data.get("best_oa_location") or {}
        if isinstance(best_location, dict):
            return best_location.get("pdf_url") or best_location.get("url_for_pdf") or best_location.get("url")

        return None

    def _looks_like_pdf(self, path: Path) -> bool:
        try:
            with path.open("rb") as file:
                return file.read(4) == b"%PDF"
        except OSError:
            return False
