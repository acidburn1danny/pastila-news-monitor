"""Pluggable source adapters for Pastila Scout."""

from pastila_scout.adapters.base import SourceAdapter
from pastila_scout.adapters.html import HTMLAdapter
from pastila_scout.adapters.registry import (
    UnsupportedSourceTypeError,
    get_adapter,
    register_adapter,
)
from pastila_scout.adapters.rss import RSSAdapter

__all__ = [
    "HTMLAdapter",
    "RSSAdapter",
    "SourceAdapter",
    "UnsupportedSourceTypeError",
    "get_adapter",
    "register_adapter",
]
