"""Açık erişim PDF indirme modülü."""

import os
import time
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import requests

from .config import UNPAYWALL_API
from .utils import setup_logging, sanitize_filename, ensure_dir, is_valid_doi

logger = setup_logging()


class PDFDownloader:
    """
    Unpaywall API üzerinden yasal açık erişim PDF'leri indirir.
    Sci-Hub veya benzeri gri alan siteler kullanılmaz.
    """

    def __init__(
        self,
        pdf_dir: str = "output/pdfs",
        email: Optional[str] = None,
        timeout: int = 30,
    ):
        self.pdf_dir = ensure_dir(pdf_dir)
        self.email = email or os.getenv("UNPAYWALL_EMAIL", "user@example.com")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "WoS-Search-Skill/2.0 (mailto:{})",
        })
        self.downloaded = 0
        self.failed = 0

    def download(
        self,
        doi: str,
        title: str = "",
        provided_pdf_url: str = "",
    ) -> Optional[str]:
        """
        DOI için açık erişim PDF'sini indir.

        Returns:
            İndirilen dosyanın yolu veya None.
        """
        if not is_valid_doi(doi):
            self.failed += 1
            return None

        # Dosya adı: doi_sanitized_title.pdf
        safe_title = sanitize_filename(title) if title else sanitize_filename(doi)
        filename = f"{safe_title}.pdf"
        filepath = self.pdf_dir / filename

        # Zaten varsa tekrar indirme
        if filepath.exists():
            logger.debug(f"PDF zaten mevcut: {filename}")
            return str(filepath)

        pdf_url = provided_pdf_url

        # Eğer URL verilmemişse Unpaywall'dan bul
        if not pdf_url:
            pdf_url = self._resolve_via_unpaywall(doi)

        if not pdf_url:
            self.failed += 1
            return None

        # İndir
        try:
            time.sleep(0.5)
            resp = self.session.get(
                pdf_url,
                timeout=self.timeout,
                stream=True,
            )
            resp.raise_for_status()

            # PDF doğrulama
            content_type = resp.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower():
                # Bazen redirect veya HTML gelir
                first_bytes = resp.raw.read(4)
                resp.raw.close()
                if first_bytes[:4] != b"%PDF":
                    logger.warning(f"PDF değil ({doi}): content-type={content_type}")
                    self.failed += 1
                    return None
                # Tekrar aç
                resp = self.session.get(pdf_url, timeout=self.timeout, stream=True)

            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            size_kb = filepath.stat().st_size / 1024
            logger.info(f"PDF indirildi ({size_kb:.1f} KB): {filename}")
            self.downloaded += 1
            return str(filepath)

        except Exception as e:
            logger.warning(f"PDF indirme hatası ({doi}): {e}")
            self.failed += 1
            if filepath.exists():
                filepath.unlink()
            return None

    def _resolve_via_unpaywall(self, doi: str) -> Optional[str]:
        """Unpaywall API ile açık erişim PDF URL'si çözümle."""
        url = UNPAYWALL_API.format(doi=doi, email=self.email)
        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json()
            best_oa = data.get("best_oa_location")
            if best_oa and best_oa.get("url_for_pdf"):
                return best_oa["url_for_pdf"]
            # Alternatif lokasyonlar
            for loc in data.get("oa_locations", []):
                if loc.get("url_for_pdf"):
                    return loc["url_for_pdf"]
            return None
        except Exception as e:
            logger.debug(f"Unpaywall hatası ({doi}): {e}")
            return None
