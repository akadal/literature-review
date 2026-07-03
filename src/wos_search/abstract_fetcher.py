"""Abstract ve metadata çekme modülü."""

import re
import time
from typing import Optional, Dict, Any, Tuple

import requests

from .config import (
    SEMANTIC_SCHOLAR_API,
    CROSSREF_API,
    OPENALEX_API,
    DEFAULT_HEADERS,
)
from .utils import setup_logging, sleep_with_backoff

logger = setup_logging()


class AbstractFetcher:
    """
    Makale abstract'ını ve ek metadata'yı birden fazla açık API'den çeker.
    Öncelik sırası:
        1. Semantic Scholar (hızlı, kapsamlı)
        2. OpenAlex (zengin metadata)
        3. Crossref (yedek)
    """

    def __init__(self, request_timeout: int = 15):
        self.timeout = request_timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def fetch(self, doi: str) -> Tuple[str, Dict[str, Any]]:
        """
        DOI üzerinden abstract ve metadata çek.

        Returns:
            (abstract_text, metadata_dict)
        """
        if not doi:
            return "", {}

        doi = doi.strip()
        meta: Dict[str, Any] = {}

        # 1. Semantic Scholar
        abstract, meta = self._fetch_semantic_scholar(doi)
        if abstract and len(abstract) > 50:
            logger.debug(f"[SS] Abstract bulundu: {doi}")
            return abstract, meta

        # 2. OpenAlex
        abstract, meta = self._fetch_openalex(doi)
        if abstract and len(abstract) > 50:
            logger.debug(f"[OA] Abstract bulundu: {doi}")
            return abstract, meta

        # 3. Crossref
        abstract, meta = self._fetch_crossref(doi)
        if abstract and len(abstract) > 50:
            logger.debug(f"[CR] Abstract bulundu: {doi}")
            return abstract, meta

        logger.warning(f"Abstract bulunamadı: {doi}")
        return "", meta

    def _fetch_semantic_scholar(self, doi: str) -> Tuple[str, Dict[str, Any]]:
        """Semantic Scholar'dan abstract ve PDF bağlantısı çek."""
        url = SEMANTIC_SCHOLAR_API.format(doi=doi)
        meta: Dict[str, Any] = {}
        try:
            time.sleep(0.5)  # rate limit koruması
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 429:
                sleep_with_backoff(1, base=2.0)
                resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return "", meta

            data = resp.json()
            abstract = data.get("abstract", "")
            oa = data.get("openAccessPdf")
            if oa:
                meta["pdf_url"] = oa.get("url", "")
            return abstract.strip() if abstract else "", meta
        except Exception as e:
            logger.debug(f"Semantic Scholar hatası ({doi}): {e}")
            return "", meta

    def _fetch_openalex(self, doi: str) -> Tuple[str, Dict[str, Any]]:
        """OpenAlex'ten abstract çek (inverted index formatı)."""
        url = OPENALEX_API.format(doi=doi)
        meta: Dict[str, Any] = {}
        try:
            time.sleep(0.5)
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return "", meta
            data = resp.json()

            # OpenAlex abstract inverted index
            inverted = data.get("abstract_inverted_index")
            if inverted:
                abstract = self._reconstruct_openalex_abstract(inverted)
                oa_info = data.get("open_access", {})
                if oa_info.get("is_oa"):
                    meta["pdf_url"] = oa_info.get("oa_url", "")
                return abstract, meta

            return "", meta
        except Exception as e:
            logger.debug(f"OpenAlex hatası ({doi}): {e}")
            return "", meta

    @staticmethod
    def _reconstruct_openalex_abstract(inverted_index: Dict[str, Any]) -> str:
        """OpenAlex inverted index abstract'ını düz metne çevir."""
        if not inverted_index:
            return ""
        max_pos = 0
        word_map: Dict[int, str] = {}
        for word, positions in inverted_index.items():
            for pos in positions:
                word_map[pos] = word
                if pos > max_pos:
                    max_pos = pos
        words = [word_map.get(i, "") for i in range(max_pos + 1)]
        return " ".join(words)

    def _fetch_crossref(self, doi: str) -> Tuple[str, Dict[str, Any]]:
        """Crossref'ten abstract çek."""
        url = CROSSREF_API.format(doi=doi)
        meta: Dict[str, Any] = {}
        try:
            time.sleep(0.5)
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return "", meta
            data = resp.json()
            msg = data.get("message", {})
            abstract = msg.get("abstract", "")
            if abstract:
                # JATS XML temizliği
                clean = re.sub(r"<[^>]+>", "", abstract)
                return clean.strip(), meta
            return "", meta
        except Exception as e:
            logger.debug(f"Crossref hatası ({doi}): {e}")
            return "", meta
