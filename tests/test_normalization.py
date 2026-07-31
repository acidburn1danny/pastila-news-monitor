import pytest

from pastila_scout.normalization import normalize_title, normalize_url


def test_url_removes_tracking_parameters_and_preserves_meaningful_ones() -> None:
    url = (
        " https://Example.COM/search?page=2&utm_source=newsletter"
        "&fbclid=tracking&category=local "
    )

    assert normalize_url(url) == ("https://example.com/search?category=local&page=2")


def test_url_query_sorting_is_deterministic() -> None:
    first = normalize_url("https://example.com/items?z=2&a=3&a=1")
    second = normalize_url("https://example.com/items?a=1&z=2&a=3")

    assert first == second == "https://example.com/items?a=1&a=3&z=2"


def test_url_removes_fragment_and_default_ports() -> None:
    assert normalize_url("HTTP://Example.com:80/news#latest") == (
        "http://example.com/news"
    )
    assert normalize_url("https://Example.com:443/news#latest") == (
        "https://example.com/news"
    )


def test_url_collapses_path_slashes_and_handles_trailing_slash() -> None:
    assert normalize_url("https://example.com//news///today/") == (
        "https://example.com/news/today"
    )
    assert normalize_url("https://example.com/") == "https://example.com/"


@pytest.mark.parametrize(
    "url",
    [
        "",
        "example.com/news",
        "ftp://example.com/news",
        "https:///news",
        "https://example.com:invalid/news",
        "https://exa mple.com/news",
        "https://example.com/%broken",
    ],
)
def test_url_rejects_malformed_values(url: str) -> None:
    with pytest.raises(ValueError, match="URL|url"):
        normalize_url(url)


def test_title_normalizes_whitespace_and_case() -> None:
    assert normalize_title("  Știri\n\t  Locale  ") == "știri locale"


def test_title_normalizes_romanian_diacritic_variants() -> None:
    assert normalize_title("Ştiinţă şi Ţară") == "știință și țară"


def test_title_normalizes_unicode_composition() -> None:
    composed = "Café"
    decomposed = "Cafe\u0301"

    assert normalize_title(composed) == normalize_title(decomposed) == "café"


def test_title_removes_quotes_and_repeated_decorative_punctuation() -> None:
    assert normalize_title(" „Breaking!!! News???” ") == "breaking news"


def test_title_output_is_deterministic() -> None:
    title = "  «ŞTIRI --- Locale»  "

    assert normalize_title(title) == normalize_title(title) == "știri locale"
