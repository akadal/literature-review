"""Web of Science Starter API istemcisi."""

import os
import time
from typing import Optional, Dict, Any, List

import requests
from dotenv import load_dotenv

from .config import WOS_BASE_URL, WOS_PAGE_SIZE, DEFAULT_HEADERS
from .utils import sleep_with_backoff, setup_logging

# .env otomatik yükle
load_dotenv()

logger = setup_logging()


class WosAPIError(Exception):
    """WoS API özel hata sınıfı."""
    pass


class WosClient:
    """
    Web of Science Starter API ile güvenli ve robust iletişim sağlar.
    Rate limiting, retry logic ve hata yönetimi içerir.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("WOS_API_KEY")
        if not self.api_key or self.api_key.strip() in (
            "",
            "buraya_api_anahtarinizi_yazin",
            "your_api_key_here",
        ):
            raise WosAPIError(
                "WOS_API_KEY bulunamadı! Lütfen .env dosyasını kontrol edin."
            )

        self.session = requests.Session()
        self.session.headers.update({
            **DEFAULT_HEADERS,
            "X-ApiKey": self.api_key,
        })
        self.last_request_time: Optional[float] = None
        self.total_requests = 0

    def _rate_limit(self) -> None:
        """İstekler arası bekleme (max 5 istek/saniye)."""
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            min_interval = 0.22  # ~4.5 req/s (güvenlik payı)
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
        self.last_request_time = time.time()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retries: int = 3,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """HTTP isteği gönder ve retry logic uygula."""
        url = f"{WOS_BASE_URL}{endpoint}"
        last_exception: Optional[Exception] = None

        for attempt in range(retries):
            self._rate_limit()
            try:
                self.total_requests += 1
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    timeout=timeout,
                )

                if response.status_code == 429:
                    logger.warning("Rate limit aşıldı (429). Bekleniyor...")
                    sleep_with_backoff(attempt, base=2.0)
                    continue

                if response.status_code == 401:
                    raise WosAPIError("API anahtarı geçersiz (401 Unauthorized).")

                if response.status_code == 400:
                    raise WosAPIError(
                        f"Geçersiz sorgu (400): {response.text}"
                    )

                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout:
                logger.warning(f"Zaman aşımı (attempt {attempt + 1}/{retries})")
                sleep_with_backoff(attempt)
                last_exception = requests.exceptions.Timeout("İstek zaman aşımına uğradı.")

            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Bağlantı hatası (attempt {attempt + 1}/{retries}): {e}")
                sleep_with_backoff(attempt)
                last_exception = e

            except requests.exceptions.HTTPError as e:
                if response.status_code >= 500:
                    logger.warning(f"Sunucu hatası {response.status_code}, retry...")
                    sleep_with_backoff(attempt)
                    last_exception = e
                else:
                    raise WosAPIError(f"HTTP Hatası {response.status_code}: {e}")

        raise WosAPIError(f"Maksimum retry sayısına ulaşıldı: {last_exception}")

    def search(
        self,
        query: str,
        editions: str,
        page: int = 1,
        limit: int = WOS_PAGE_SIZE,
        sort_field: str = "RS+D",
    ) -> Dict[str, Any]:
        """
        WoS doküman araması yap.

        Returns:
            API yanıtı (hits, metadata, vs.)
        """
        params = {
            "q": query,
            "db": "WOS",
            "limit": min(limit, WOS_PAGE_SIZE),
            "page": page,
            "sortField": sort_field,
        }
        if editions:
            params["edition"] = editions

        logger.debug(f"WoS araması: page={page}, limit={limit}")
        return self._request("GET", "/documents", params=params)

    def get_document(self, uid: str) -> Dict[str, Any]:
        """UID ile tek bir doküman getir."""
        return self._request("GET", f"/documents/{uid}")

    def get_citing_articles(self, uid: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Bir makaleyi atan makaleleri getir."""
        data = self._request(
            "GET",
            f"/documents/{uid}/citing",
            params={"limit": min(limit, WOS_PAGE_SIZE)},
        )
        return data.get("hits", [])
