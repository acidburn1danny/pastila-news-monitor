"""Interface shared by source-specific ingestion adapters."""

from typing import Protocol

from pastila_scout.config import SourceConfig
from pastila_scout.http_client import HTTPClient
from pastila_scout.models import ArticleCandidate


class SourceAdapter(Protocol):
    """Adapter capable of fetching candidates from one configured source."""

    def fetch(
        self, source: SourceConfig, http_client: HTTPClient
    ) -> list[ArticleCandidate]:
        """Fetch and parse all article candidates currently exposed by *source*."""

        ...
