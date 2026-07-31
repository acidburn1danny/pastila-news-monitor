import pytest

from pastila_scout.adapters.html import HTMLAdapter
from pastila_scout.config import SourceConfig


class FakeHTTPClient:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.requested_url: str | None = None

    def fetch(self, url: str) -> bytes:
        self.requested_url = url
        return self.content


def html_source(**updates: object) -> SourceConfig:
    values: dict[str, object] = {
        "id": "site",
        "name": "Site",
        "type": "html",
        "url": "https://example.com/news/index.html",
        "enabled": True,
        "categories": ["Diverse"],
        "list_selector": "article",
        "link_selector": "a.story",
    }
    values.update(updates)
    return SourceConfig.model_validate(values)


def test_basic_extraction_relative_url_and_link_title_fallback() -> None:
    client = FakeHTTPClient(
        b'<article><a class="story" href="../story/1/">  First   Story </a></article>'
    )

    candidates = HTMLAdapter().fetch(html_source(), client)  # type: ignore[arg-type]

    assert client.requested_url == "https://example.com/news/index.html"
    assert len(candidates) == 1
    assert candidates[0].url == "https://example.com/story/1"
    assert candidates[0].title == "first story"
    assert candidates[0].raw_payload == {
        "href": "../story/1/",
        "title": "First   Story",
    }


def test_configured_title_summary_and_base_url() -> None:
    html = b"""<article>
      <a class="story" href="item/2">Link fallback</a>
      <h2>Selected TITLE!!!</h2><p class="summary">Useful summary</p>
    </article>"""
    source = html_source(
        title_selector="h2",
        summary_selector=".summary",
        base_url="https://cdn.example.com/archive/",
    )

    candidate = HTMLAdapter().fetch(source, FakeHTTPClient(html))[0]  # type: ignore[arg-type]

    assert candidate.url == "https://cdn.example.com/archive/item/2"
    assert candidate.title == "selected title"
    assert candidate.summary == "Useful summary"
    assert candidate.raw_payload["summary"] == "Useful summary"


@pytest.mark.parametrize(
    ("markup", "expected"),
    [
        (
            '<time datetime="2025-04-03T14:30:00+02:00">ignored</time>',
            "2025-04-03T12:30:00+00:00",
        ),
        ("<time>Tue, 21 Jan 2025 10:30:00 +0200</time>", "2025-01-21T08:30:00+00:00"),
        ("<time>not a date</time>", None),
    ],
)
def test_publication_date_parsing(markup: str, expected: str | None) -> None:
    html = (
        '<article><a class="story" href="/story">Story</a>' f"{markup}</article>"
    ).encode()

    candidate = HTMLAdapter().fetch(
        html_source(date_selector="time"), FakeHTTPClient(html)  # type: ignore[arg-type]
    )[0]

    assert candidate.published_at == expected
    assert candidate.raw_payload is not None
    assert "date" in candidate.raw_payload


def test_malformed_entries_are_isolated_and_duplicate_urls_are_removed() -> None:
    html = b"""
      <article><a class="story">Missing href</a></article>
      <article><a class="story" href="not-a-url">Relative is valid</a></article>
      <article><a class="story" href="http://">Malformed URL</a></article>
      <article><a class="story" href="/same?utm_source=one">First</a></article>
      <article><a class="story" href="/same?fbclid=two">Duplicate</a></article>
      <article><span>No matching link</span></article>
    """

    candidates = HTMLAdapter().fetch(html_source(), FakeHTTPClient(html))  # type: ignore[arg-type]

    assert [candidate.title for candidate in candidates] == [
        "relative is valid",
        "first",
    ]


def test_max_items_counts_only_valid_unique_entries() -> None:
    html = b"""
      <article><a class="story">Invalid</a></article>
      <article><a class="story" href="/one">One</a></article>
      <article><a class="story" href="/one">Duplicate</a></article>
      <article><a class="story" href="/two">Two</a></article>
      <article><a class="story" href="/three">Three</a></article>
    """

    candidates = HTMLAdapter().fetch(
        html_source(max_items=2), FakeHTTPClient(html)  # type: ignore[arg-type]
    )

    assert [candidate.title for candidate in candidates] == ["one", "two"]
