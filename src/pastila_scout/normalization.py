"""Deterministic normalization utilities for article URLs and titles."""

import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_PARAMETERS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
    }
)
_SURROUNDING_QUOTES = frozenset("\"'“”„‟«»‹›")
_INVALID_PERCENT_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")


def normalize_url(url: str) -> str:
    """Normalize an absolute HTTP(S) URL for deterministic comparison.

    Tracking parameters and fragments are discarded. Meaningful query pairs
    are retained and sorted by name and value.

    Raises:
        ValueError: If *url* is not a well-formed absolute HTTP(S) URL.
    """

    candidate = url.strip()
    if not candidate:
        raise ValueError("URL must not be empty")
    if any(character.isspace() for character in candidate):
        raise ValueError(f"Malformed URL: whitespace is not allowed in {url!r}")
    if _INVALID_PERCENT_ESCAPE.search(candidate):
        raise ValueError(f"Malformed URL: invalid percent escape in {url!r}")

    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"Malformed URL {url!r}: {exc}") from exc

    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"Malformed URL {url!r}: scheme must be HTTP or HTTPS")
    if not parsed.hostname:
        raise ValueError(f"Malformed URL {url!r}: hostname is required")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"Malformed URL {url!r}: credentials are not supported")

    hostname = parsed.hostname.lower()
    if any(character.isspace() for character in hostname):
        raise ValueError(f"Malformed URL {url!r}: invalid hostname")
    if ":" in hostname:
        hostname = f"[{hostname}]"

    is_default_port = (scheme == "http" and port == 80) or (
        scheme == "https" and port == 443
    )
    netloc = hostname if port is None or is_default_port else f"{hostname}:{port}"

    path = re.sub(r"/{2,}", "/", parsed.path)
    if path != "/":
        path = path.rstrip("/")

    query_pairs = [
        (name, value)
        for name, value in parse_qsl(parsed.query, keep_blank_values=True)
        if name.lower() not in _TRACKING_PARAMETERS
    ]
    query = urlencode(sorted(query_pairs))

    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_title(title: str) -> str:
    """Normalize an article title into a deterministic comparison string."""

    normalized = unicodedata.normalize("NFKC", title).strip()
    normalized = normalized.translate(
        str.maketrans({"ş": "ș", "Ş": "Ș", "ţ": "ț", "Ţ": "Ț"})
    )
    normalized = _remove_surrounding_quotes(normalized)
    normalized = _remove_decorative_punctuation(normalized)
    normalized = " ".join(normalized.split())
    return normalized.lower()


def _remove_surrounding_quotes(title: str) -> str:
    """Remove paired quotation characters surrounding an entire title."""

    while (
        len(title) >= 2
        and title[0] in _SURROUNDING_QUOTES
        and title[-1] in _SURROUNDING_QUOTES
    ):
        title = title[1:-1].strip()
    return title


def _remove_decorative_punctuation(title: str) -> str:
    """Replace runs of two or more punctuation characters with one space."""

    result: list[str] = []
    index = 0
    while index < len(title):
        if not unicodedata.category(title[index]).startswith("P"):
            result.append(title[index])
            index += 1
            continue

        end = index + 1
        while end < len(title) and unicodedata.category(title[end]).startswith("P"):
            end += 1
        punctuation = title[index:end]
        result.append(" " if len(punctuation) > 1 else punctuation)
        index = end

    return "".join(result)
