"""Pastila news monitoring package."""

import re
from importlib import metadata

_DISTRIBUTION_NAME = "pastila-news-monitor"
_DEVELOPMENT_VERSION = "0.0.0-dev"
_STABLE_VERSION_PATTERN = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)",
    flags=re.ASCII,
)


def _project_version() -> str:
    try:
        candidate = metadata.version(_DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError:
        return _DEVELOPMENT_VERSION
    if (
        type(candidate) is not str
        or len(candidate) > 128
        or not candidate.isascii()
        or _STABLE_VERSION_PATTERN.fullmatch(candidate) is None
    ):
        raise RuntimeError("invalid installed package version") from None
    return candidate


__version__ = _project_version()
