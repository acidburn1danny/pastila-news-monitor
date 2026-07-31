"""Reusable HTTP transport for Scout feed downloads."""

import logging
from types import TracebackType
from typing import Self

import httpx

logger = logging.getLogger(__name__)
USER_AGENT = "Pastila Scout/0.1 (+news feed monitor)"


class HTTPClientError(RuntimeError):
    """Base error raised for an unsuccessful HTTP fetch."""


class HTTPTimeoutError(HTTPClientError):
    """Raised when an HTTP request exceeds its timeout."""


class HTTPNetworkError(HTTPClientError):
    """Raised when a network or protocol error prevents a response."""


class HTTPResponseError(HTTPClientError):
    """Raised when a server returns a non-success response."""


class HTTPClient:
    """Context-managed, reusable HTTP client for downloading feed bytes."""

    def __init__(self, timeout: float = 20.0) -> None:
        """Configure the client with a request timeout in seconds."""

        self._timeout = timeout
        self._client: httpx.Client | None = None

    def __enter__(self) -> Self:
        """Open the underlying HTTP connection pool."""

        self._client = httpx.Client(
            timeout=self._timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the underlying HTTP connection pool."""

        if self._client is not None:
            self._client.close()
            self._client = None

    def fetch(self, url: str) -> bytes:
        """Fetch *url* and return its response body as bytes.

        Raises:
            HTTPTimeoutError: If the request times out.
            HTTPNetworkError: If no usable response can be obtained.
            HTTPResponseError: If the response status is not successful.
        """

        if self._client is None:
            raise RuntimeError("HTTPClient must be used as a context manager")

        logger.info("HTTP request started url=%s", url)
        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.error("HTTP timeout url=%s", url)
            raise HTTPTimeoutError(f"Request timed out for {url}") from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "HTTP response error url=%s status=%d",
                url,
                exc.response.status_code,
            )
            raise HTTPResponseError(
                f"HTTP {exc.response.status_code} while fetching {url}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("HTTP network failure url=%s reason=%s", url, exc)
            raise HTTPNetworkError(
                f"Network error while fetching {url}: {exc}"
            ) from exc

        logger.info(
            "HTTP response received url=%s status=%d bytes=%d",
            url,
            response.status_code,
            len(response.content),
        )
        return response.content
