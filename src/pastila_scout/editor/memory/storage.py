"""UTF-8, atomic persistence for cumulative editorial memory snapshots."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from pastila_scout.editor.memory.models import EditorialMemory


def load_memory(path: Path) -> EditorialMemory:
    """Load memory, returning an empty versioned state when no file exists."""

    if not path.exists():
        return EditorialMemory()
    return EditorialMemory.model_validate_json(path.read_text(encoding="utf-8"))


def save_memory(path: Path, memory: EditorialMemory) -> None:
    """Atomically write a validated editorial-memory snapshot as UTF-8 JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(memory.model_dump_json(indent=2))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise
