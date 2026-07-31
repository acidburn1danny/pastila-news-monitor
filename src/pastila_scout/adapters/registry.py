"""Registry of source type names to adapter instances."""

from pastila_scout.adapters.base import SourceAdapter
from pastila_scout.adapters.html import HTMLAdapter
from pastila_scout.adapters.rss import RSSAdapter


class UnsupportedSourceTypeError(LookupError):
    """Raised when no adapter is registered for a source type."""


_ADAPTERS: dict[str, SourceAdapter] = {
    "rss": RSSAdapter(),
    "html": HTMLAdapter(),
}


def register_adapter(source_type: str, adapter: SourceAdapter) -> None:
    """Register or replace the adapter used for *source_type*."""

    if not source_type:
        raise ValueError("Source type must not be empty")
    _ADAPTERS[source_type] = adapter


def get_adapter(source_type: str) -> SourceAdapter:
    """Return the registered adapter for *source_type*.

    Raises:
        UnsupportedSourceTypeError: If the source type has no registered adapter.
    """

    try:
        return _ADAPTERS[source_type]
    except KeyError as exc:
        raise UnsupportedSourceTypeError(
            f"Unsupported source type: {source_type!r}"
        ) from exc
