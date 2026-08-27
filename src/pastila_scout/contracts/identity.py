"""Canonical serialization and stable report identity."""

import hashlib
import json
from typing import Any

from pydantic import BaseModel
from pydantic_core import to_jsonable_python

from pastila_scout.contracts.scout_editor import ScoutEditorInputV1


def canonical_json_bytes(value: BaseModel | dict[str, Any]) -> bytes:
    """Serialize as deterministic compact UTF-8 JSON without non-finite numbers."""

    data = (
        value.model_dump(mode="json")
        if isinstance(value, BaseModel)
        else to_jsonable_python(value)
    )
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def scout_input_identity(value: ScoutEditorInputV1 | dict[str, Any]) -> tuple[str, str]:
    """Hash every public editorial field while blanking the two identity fields."""

    data = (
        value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    )
    projection = dict(data)
    projection["report_id"] = ""
    projection["content_fingerprint"] = ""
    digest = hashlib.sha256(canonical_json_bytes(projection)).hexdigest()
    return f"scout-editor-input-v1:sha256:{digest}", f"sha256:{digest}"


def _legacy_scout_input_identity_without_event_authority(
    value: ScoutEditorInputV1,
) -> tuple[str, str] | None:
    """Project the exact pre-1.1.5 contract when the new field was absent.

    Pydantic retains which input fields were supplied.  That lets historical
    payloads be distinguished from current payloads that explicitly bind an
    authority bundle (including an explicit ``null`` fallback).
    """

    if not value.ranked_events or any(
        "event_authority_bundle" in event.model_fields_set
        for event in value.ranked_events
    ):
        return None
    projection = value.model_dump(mode="json")
    for event in projection["ranked_events"]:
        event.pop("event_authority_bundle")
    return scout_input_identity(projection)


def assign_scout_input_identity(data: dict[str, Any]) -> ScoutEditorInputV1:
    """Validate data after calculating its stable public identity."""

    placeholder = dict(data)
    placeholder["report_id"] = f"scout-editor-input-v1:sha256:{'0' * 64}"
    placeholder["content_fingerprint"] = f"sha256:{'0' * 64}"
    validated = ScoutEditorInputV1.model_validate_json(
        canonical_json_bytes(placeholder)
    )
    report_id, fingerprint = scout_input_identity(validated)
    return validated.model_copy(
        update={"report_id": report_id, "content_fingerprint": fingerprint}
    )


def verify_scout_input_identity(value: ScoutEditorInputV1) -> None:
    """Reject a valid-looking contract whose content was changed after export."""

    report_id, fingerprint = scout_input_identity(value)
    if value.report_id == report_id and value.content_fingerprint == fingerprint:
        return
    legacy_identity = _legacy_scout_input_identity_without_event_authority(value)
    if legacy_identity is not None and (
        value.report_id,
        value.content_fingerprint,
    ) == legacy_identity:
        return
    raise ValueError("Scout contract identity does not match its content")
