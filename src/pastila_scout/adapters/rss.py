"""RSS source adapter."""

import logging

from pastila_scout.config import SourceConfig
from pastila_scout.http_client import HTTPClient
from pastila_scout.models import ArticleCandidate
from pastila_scout.rss import parse_feed

logger = logging.getLogger(__name__)


class RSSAdapter:
    """Fetch and parse RSS or Atom sources using existing Scout services."""

    def fetch(
        self, source: SourceConfig, http_client: HTTPClient
    ) -> list[ArticleCandidate]:
        """Download *source* and return its parsed article candidates."""

        candidates = parse_feed(source.id, http_client.fetch(source.url))
        logger.info(
            "RSS feed parsed source=%s candidates=%d", source.id, len(candidates)
        )
        return candidates
