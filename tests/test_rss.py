import json

import pytest

from pastila_scout.rss import FeedParseError, parse_feed

RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example News</title>
    <link>https://example.com/</link>
    <description>Example feed</description>
    <item>
      <title>  ŞTIRI   Locale!!!  </title>
      <link>HTTPS://Example.COM:443//article/?utm_source=feed&amp;id=2</link>
      <description>A local summary</description>
      <pubDate>Tue, 21 Jan 2025 10:30:00 +0200</pubDate>
    </item>
  </channel>
</rss>
"""


ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example Atom</title>
  <id>https://example.com/atom</id>
  <updated>2025-02-03T12:00:00Z</updated>
  <entry>
    <title>Atom Article</title>
    <id>article-1</id>
    <link href="https://example.com/atom-article" />
    <summary>Atom summary</summary>
    <updated>2025-02-03T12:00:00Z</updated>
  </entry>
</feed>
"""


def test_parses_rss_with_normalization_summary_and_published_date() -> None:
    candidates = parse_feed("rss-source", RSS_FEED)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.source_id == "rss-source"
    assert candidate.url == "https://example.com/article?id=2"
    assert candidate.title == "știri locale"
    assert candidate.summary == "A local summary"
    assert candidate.published_at == "2025-01-21T08:30:00+00:00"
    assert candidate.raw_payload is not None
    json.dumps(candidate.raw_payload)


def test_parses_atom_and_uses_updated_date_fallback() -> None:
    candidates = parse_feed("atom-source", ATOM_FEED.encode())

    assert len(candidates) == 1
    assert candidates[0].summary == "Atom summary"
    assert candidates[0].published_at == "2025-02-03T12:00:00+00:00"


@pytest.mark.parametrize("source_id", ["bbc_world", "politico_europe", "msnow"])
def test_enabled_international_rss_shapes_parse_offline(source_id: str) -> None:
    candidates = parse_feed(source_id, RSS_FEED)

    assert len(candidates) == 1
    assert candidates[0].source_id == source_id
    assert candidates[0].published_at == "2025-01-21T08:30:00+00:00"


def test_skips_entries_without_url_or_title_and_isolates_malformed_entry() -> None:
    feed = """<rss version="2.0"><channel>
      <title>Mixed</title><link>https://example.com</link><description>Mixed</description>
      <item><title>No URL</title><description>Skipped</description></item>
      <item><link>https://example.com/no-title</link></item>
      <item><title>Bad URL</title><link>not-a-url</link></item>
      <item><title>Valid</title><link>https://example.com/valid</link></item>
    </channel></rss>"""

    candidates = parse_feed("mixed-source", feed)

    assert [candidate.title for candidate in candidates] == ["valid"]


def test_rejects_malformed_feed() -> None:
    with pytest.raises(FeedParseError, match="Malformed"):
        parse_feed("source", "<rss><channel><item></rss>")


def test_rejects_unrecognized_xml() -> None:
    with pytest.raises(FeedParseError, match="recognizable"):
        parse_feed("source", "<document><title>Not a feed</title></document>")


def test_prevents_duplicates_by_normalized_url() -> None:
    feed = """<rss version="2.0"><channel>
      <title>Duplicates</title><link>https://example.com</link><description>Duplicates</description>
      <item>
        <title>First</title>
        <link>https://example.com/article?utm_source=one&amp;id=7</link>
      </item>
      <item>
        <title>Second</title>
        <link>HTTPS://EXAMPLE.COM:443//article/?id=7&amp;fbclid=two</link>
      </item>
    </channel></rss>"""

    candidates = parse_feed("source", feed)

    assert len(candidates) == 1
    assert candidates[0].url == "https://example.com/article?id=7"
    assert candidates[0].title == "first"
