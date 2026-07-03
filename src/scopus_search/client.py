"""Client wrapper for the Elsevier Scopus API."""

from __future__ import annotations

import os
import time
from typing import Any, Optional

try:
    import requests
except ImportError:  # pragma: no cover - exercised only in minimal environments.
    requests = None  # type: ignore[assignment]

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is declared, this keeps imports graceful.

    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False


from .config import DEFAULT_HEADERS, SCOPUS_PAGE_SIZE, SCOPUS_RATE_LIMIT_RPS, SCOPUS_SEARCH_URL
from .utils import setup_logging, sleep_with_backoff

logger = setup_logging(verbose=False)


class ScopusAPIError(Exception):
    """Raised when the Scopus API request cannot be completed."""


def _require_requests() -> Any:
    if requests is None:
        raise ScopusAPIError(
            "The 'requests' package is required for Scopus API calls. "
            "Install the project with `pip install -e .`."
        )
    return requests


class ScopusClient:
    """Small requests-based client for Scopus search requests."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        insttoken: Optional[str] = None,
        session: Optional[Any] = None,
    ) -> None:
        load_dotenv()
        requests_module = _require_requests()

        self.api_key = api_key or os.getenv("SCOPUS_API_KEY")
        self.insttoken = insttoken or os.getenv("SCOPUS_INSTTOKEN")

        if not self.api_key:
            raise ScopusAPIError("SCOPUS_API_KEY is required. Set it in the environment or pass api_key.")

        self.session = session or requests_module.Session()
        headers = dict(DEFAULT_HEADERS)
        headers["X-ELS-APIKey"] = self.api_key
        if self.insttoken:
            headers["X-ELS-Insttoken"] = self.insttoken

        self.session.headers.update(headers)
        self.last_request_time: Optional[float] = None
        self.total_requests = 0

    def _rate_limit(self) -> None:
        min_interval = 1.0 / max(SCOPUS_RATE_LIMIT_RPS, 1)

        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)

        self.last_request_time = time.time()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        retries: int = 3,
        timeout: int = 30,
    ) -> dict[str, Any]:
        url = SCOPUS_SEARCH_URL if endpoint == "/search" else endpoint
        attempts = max(1, retries)
        last_exception: Optional[Exception] = None

        for attempt in range(attempts):
            response: Optional[requests.Response] = None
            self._rate_limit()

            try:
                self.total_requests += 1
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=timeout,
                )

                if response.status_code == 429:
                    last_exception = ScopusAPIError("Scopus rate limit exceeded (429).")
                    if attempt < attempts - 1:
                        logger.warning("Scopus rate limit exceeded (429). Retrying...")
                        sleep_with_backoff(attempt, base=2.0)
                        continue
                    raise last_exception

                if response.status_code == 401:
                    raise ScopusAPIError("Scopus API key was rejected (401 Unauthorized).")

                if response.status_code == 400:
                    raise ScopusAPIError(f"Invalid Scopus query (400): {response.text}")

                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout as exc:
                logger.warning("Scopus request timed out (attempt %s/%s).", attempt + 1, attempts)
                sleep_with_backoff(attempt)
                last_exception = exc
            except requests.exceptions.ConnectionError as exc:
                logger.warning(
                    "Scopus connection failed (attempt %s/%s): %s",
                    attempt + 1,
                    attempts,
                    exc,
                )
                sleep_with_backoff(attempt)
                last_exception = exc
            except requests.exceptions.HTTPError as exc:
                status = response.status_code if response is not None else None
                if status and status >= 500 and attempt < attempts - 1:
                    logger.warning("Scopus server returned %s. Retrying...", status)
                    sleep_with_backoff(attempt)
                    last_exception = exc
                    continue
                raise ScopusAPIError(f"Scopus HTTP error {status}: {exc}") from exc
            except ValueError as exc:
                raise ScopusAPIError("Scopus returned a response that was not valid JSON.") from exc

        raise ScopusAPIError(f"Scopus request failed after {attempts} attempts: {last_exception}")

    def search(
        self,
        query: str,
        start: int = 0,
        count: int = SCOPUS_PAGE_SIZE,
        sort: str = "relevancy",
        field: Optional[str] = None,
        view: str = "STANDARD",
    ) -> dict[str, Any]:
        """Run a Scopus search request and return the decoded JSON response."""

        params: dict[str, Any] = {
            "query": query,
            "start": max(0, start),
            "count": min(count, SCOPUS_PAGE_SIZE),
            "sort": sort,
            "view": view,
        }

        if field:
            params["field"] = field

        logger.debug("Scopus search request: start=%s, count=%s", start, count)
        return self._request("GET", "/search", params=params)
