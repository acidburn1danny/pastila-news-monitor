"""Safe, strict local-file import and export for public contracts."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from pastila_scout.contracts.editor_output import EditorAgentOutputV1
from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.identity import (
    canonical_json_bytes,
    verify_scout_input_identity,
)
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.contracts.selection_profile import SelectionProfileV1

MAX_SCOUT_INPUT_BYTES = 25 * 1024 * 1024
MAX_EDITOR_OUTPUT_BYTES = 10 * 1024 * 1024
MAX_CONTEXT_BYTES = 1024 * 1024

Contract = (
    ScoutEditorInputV1 | EditorAgentOutputV1 | SelectionProfileV1 | EpisodeContextV1
)
ModelT = TypeVar("ModelT", bound=BaseModel)


class ContractFileError(ValueError):
    """Raised when a contract file violates format or safety requirements."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractFileError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _validate_local_path(path: Path, *, must_exist: bool) -> Path:
    raw = str(path)
    lowered = raw.lower()
    if (
        "://" in raw
        or lowered.startswith(("http:", "https:", "ftp:", "file:"))
        or raw.startswith(("\\\\", "//"))
    ):
        raise ContractFileError("contract paths must be local filesystem paths")
    resolved = path.resolve(strict=False)
    reserved = {"CON", "PRN", "AUX", "NUL", "CLOCK$"}
    reserved.update(
        f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
    )
    if any(part.split(".", 1)[0].upper() in reserved for part in resolved.parts):
        raise ContractFileError("Windows device paths are not valid contract paths")
    if must_exist and (not resolved.is_file() or resolved.is_symlink()):
        raise ContractFileError("contract input must be a regular, non-symlink file")
    if not must_exist and resolved.exists() and resolved.is_symlink():
        raise ContractFileError("contract output cannot be a symbolic link")
    return resolved


def load_contract(path: Path) -> Contract:
    """Load, size-check, decode, validate, and identity-check one contract."""

    resolved = _validate_local_path(path, must_exist=True)
    size = resolved.stat().st_size
    if size > MAX_SCOUT_INPUT_BYTES:
        raise ContractFileError("contract file exceeds the maximum supported size")
    try:
        text = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ContractFileError("contract file must use strict UTF-8") from exc
    try:
        data = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise ContractFileError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ContractFileError("contract document must be a JSON object")
    version = data.get("contract_version")
    model: type[BaseModel]
    limit: int
    if version == "scout-editor-input-v1":
        model, limit = ScoutEditorInputV1, MAX_SCOUT_INPUT_BYTES
    elif version == "editor-agent-output-v1":
        model, limit = EditorAgentOutputV1, MAX_EDITOR_OUTPUT_BYTES
    elif version == "editor-selection-profile-v1":
        model, limit = SelectionProfileV1, MAX_CONTEXT_BYTES
    elif version == "episode-context-v1":
        model, limit = EpisodeContextV1, MAX_CONTEXT_BYTES
    else:
        raise ContractFileError(f"unsupported contract_version: {version!r}")
    if size > limit:
        raise ContractFileError(
            "contract file exceeds its contract-specific size limit"
        )
    validated = model.model_validate_json(text, strict=True)
    if isinstance(validated, ScoutEditorInputV1):
        verify_scout_input_identity(validated)
    return validated  # type: ignore[return-value]


def write_contract(value: Contract, path: Path) -> Path:
    """Atomically write canonical UTF-8 JSON to a safe local destination."""

    resolved = _validate_local_path(path, must_exist=False)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(value) + b"\n"
    descriptor, temporary_name = tempfile.mkstemp(
        dir=resolved.parent, prefix=f".{resolved.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(resolved)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return resolved
