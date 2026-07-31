import pytest

from pastila_scout.adapters.html import HTMLAdapter
from pastila_scout.adapters.registry import (
    UnsupportedSourceTypeError,
    get_adapter,
)
from pastila_scout.adapters.rss import RSSAdapter
from pastila_scout.config import SourceConfig

RSS = b"""<rss version="2.0"><channel>
  <title>News</title><link>https://example.com</link><description>News</description>
  <item><title>Adapter Article</title><link>https://example.com/article</link></item>
</channel></rss>"""


class FakeHTTPClient:
    def __init__(self) -> None:
        self.requested_url: str | None = None

    def fetch(self, url: str) -> bytes:
        self.requested_url = url
        return RSS


def test_rss_adapter_fetches_and_parses_feed() -> None:
    source = SourceConfig(
        id="news",
        name="News",
        type="rss",
        url="https://example.com/feed",
        enabled=True,
        categories=["Diverse"],
    )
    client = FakeHTTPClient()

    candidates = RSSAdapter().fetch(source, client)  # type: ignore[arg-type]

    assert client.requested_url == source.url
    assert len(candidates) == 1
    assert candidates[0].source_id == "news"
    assert candidates[0].title == "adapter article"


def test_registry_returns_rss_adapter() -> None:
    assert isinstance(get_adapter("rss"), RSSAdapter)


def test_registry_returns_html_adapter() -> None:
    assert isinstance(get_adapter("html"), HTMLAdapter)


def test_registry_rejects_unsupported_type() -> None:
    with pytest.raises(UnsupportedSourceTypeError, match="api"):
        get_adapter("api")
