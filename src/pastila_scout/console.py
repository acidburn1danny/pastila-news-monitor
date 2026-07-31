"""Unicode-safe console configuration for Scout commands."""

import os
import sys
from typing import TextIO


def configure_unicode_console() -> None:
    """Use UTF-8 for Windows console streams when they support reconfiguration."""

    if os.name != "nt":
        return
    _configure_stream(sys.stdout)
    _configure_stream(sys.stderr)


def _configure_stream(stream: TextIO) -> None:
    """Reconfigure a real text stream without assuming test doubles support it."""

    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="replace")
