"""Canonical VOICE and Chief Editor vertical slice.

VOICE is a commentary-only transformation of an accepted factual artifact.  The
ProductOrchestrator remains the sole workflow owner; a backend only proposes a
bounded commentary payload and never writes state directly.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Protocol
from pathlib import Path

from .vnext_foundation_v1 import BoundaryError, atomic_json, contained_path, object_identity
from .vnext_state_sqlite_v1 import SQLiteStateStore
from .vnext_workflow_v1 import TransitionRequest

_SHA256 = re.compile(r"[0-9a-f]{64}")
FACTUAL_KINDS = frozenset({"ACCEPTED_SETUP", "SOURCE_FALLBACK"})


class VoiceBoundaryError(BoundaryError):
    pass


class VoiceBackend(Protocol):
    backend_identity: str
    model_identity: str
    decoding_identity: str

    def realize(self, request: Mapping[str, object]) -> Mapping[str, object]: ...


def _identity(value: Mapping[str, object], key: str) -> str:
    actual = value.get(key)
    expected = object_identity({name: item for name, item in value.items() if name != key})
    if not isinstance(actual, str) or actual != expected:
        raise VoiceBoundaryError(f"{key} mismatch")
    return actual


def _owned_factual(store: SQLiteStateStore, workflow_identity: str, factual: Mapping[str, object]) -> str:
    identity = _identity(factual, "artifact_identity")
    kind = factual.get("artifact_kind")
    if (
        kind not in FACTUAL_KINDS
        or factual.get("workflow_identity") != workflow_identity
        or factual.get("eligible_for_voice") is not True
        or not isinstance(factual.get("text"), str)
        or not str(factual["text"]).strip()
    ):
        raise VoiceBoundaryError("VOICE requires an eligible factual artifact")
    with store.read() as connection:
        row = connection.execute(
            "SELECT artifact_kind,payload_identity,payload_ref FROM workflow_artifacts "
            "WHERE workflow_identity=? AND artifact_identity=?",
            (workflow_identity, identity),
        ).fetchone()
    if row is None or (row["artifact_kind"], row["payload_identity"]) != (kind, identity):
        raise VoiceBoundaryError("factual artifact is not owned by workflow")
    path = contained_path(store.root, Path(str(row["payload_ref"])), allow_missing=False)
    if json.loads(path.read_text(encoding="utf-8")) != factual:
        raise VoiceBoundaryError("factual artifact payload mismatch")
    return identity


def build_voice_draft(
    *,
    workflow_identity: str,
    factual: Mapping[str, object],
    instruction: str,
    seed: int,
    backend: VoiceBackend,
) -> dict[str, object]:
    factual_identity = _identity(factual, "artifact_identity")
    if factual.get("artifact_kind") not in FACTUAL_KINDS or factual.get("eligible_for_voice") is not True:
        raise VoiceBoundaryError("VOICE input is not factually accepted")
    if not instruction.strip() or seed < 0:
        raise VoiceBoundaryError("bounded instruction and non-negative seed required")
    for name in ("backend_identity", "model_identity", "decoding_identity"):
        if _SHA256.fullmatch(str(getattr(backend, name, ""))) is None:
            raise VoiceBoundaryError(f"valid {name} required")
    request: dict[str, object] = {
        "schema": "vnext-voice-request",
        "schema_version": 1,
        "workflow_identity": workflow_identity,
        "source_packet_identity": factual["source_packet_identity"],
        "factual_input_kind": factual["artifact_kind"],
        "factual_input_identity": factual_identity,
        "factual_setup": factual["text"],
        "instruction": instruction.strip(),
        "seed": seed,
        "backend_identity": backend.backend_identity,
        "model_identity": backend.model_identity,
        "decoding_identity": backend.decoding_identity,
    }
    request["request_identity"] = object_identity(request)
    response = backend.realize(dict(request))
    if not isinstance(response, Mapping):
        raise VoiceBoundaryError("VOICE backend response must be an object")
    if response.get("request_identity") != request["request_identity"]:
        raise VoiceBoundaryError("VOICE backend response is not bound to request")
    status = response.get("status")
    commentary = response.get("commentary")
    if status not in {"COMMENTARY", "ABSTAIN"}:
        raise VoiceBoundaryError("VOICE backend status must be COMMENTARY or ABSTAIN")
    if status == "COMMENTARY" and (not isinstance(commentary, str) or not commentary.strip()):
        raise VoiceBoundaryError("VOICE commentary is empty")
    if status == "ABSTAIN" and commentary not in {None, ""}:
        raise VoiceBoundaryError("VOICE abstention cannot contain commentary")
    if isinstance(commentary, str) and commentary.strip() == str(factual["text"]).strip():
        raise VoiceBoundaryError("VOICE commentary must remain separate from factual setup")
    result: dict[str, object] = {
        "schema": "vnext-voice-draft",
        "schema_version": 1,
        "artifact_kind": "VOICE_DRAFT",
        "workflow_identity": workflow_identity,
        "source_packet_identity": factual["source_packet_identity"],
        "factual_input_kind": factual["artifact_kind"],
        "factual_input_identity": factual_identity,
        "factual_setup": factual["text"],
        "commentary": commentary or "",
        "voice_status": status,
        "request_identity": request["request_identity"],
        "backend_identity": backend.backend_identity,
        "model_identity": backend.model_identity,
        "decoding_identity": backend.decoding_identity,
        "seed": seed,
        "repetition_identity": object_identity({"commentary": commentary or ""}),
    }
    result["artifact_identity"] = object_identity(result)
    return result


def persist_voice_draft(
    store: SQLiteStateStore,
    *,
    workflow_identity: str,
    factual: Mapping[str, object],
    draft: Mapping[str, object],
    observed_at: str,
) -> None:
    factual_identity = _owned_factual(store, workflow_identity, factual)
    draft_identity = _identity(draft, "artifact_identity")
    if (
        draft.get("schema") != "vnext-voice-draft"
        or draft.get("schema_version") != 1
        or draft.get("workflow_identity") != workflow_identity
        or draft.get("factual_input_identity") != factual_identity
        or draft.get("factual_setup") != factual.get("text")
        or draft.get("source_packet_identity") != factual.get("source_packet_identity")
    ):
        raise VoiceBoundaryError("VOICE draft provenance mismatch")
    relative = Path("blobs/voice-drafts") / f"{draft_identity}.json"
    target = contained_path(store.root, relative)
    if target.exists():
        if json.loads(target.read_text(encoding="utf-8")) != draft:
            raise VoiceBoundaryError("immutable VOICE draft conflict")
    else:
        atomic_json(target, dict(draft), root=store.root, overwrite=False)
    state = str(store.load_workflow(workflow_identity)["state"])
    if state == str(factual["artifact_kind"]):
        _transition(store, workflow_identity, state, "VOICE_PENDING", "voice:pending", factual_identity, None, "VOICE", "VOICE_REQUIRED", observed_at)
        state = "VOICE_PENDING"
    if state == "VOICE_PENDING":
        def rows(connection):
            connection.execute(
                "INSERT INTO workflow_artifacts VALUES(?,?,?,?,?,?)",
                (draft_identity, workflow_identity, "VOICE_DRAFT", draft_identity, relative.as_posix(), "vnext-voice-draft-v1"),
            )
        _transition(store, workflow_identity, "VOICE_PENDING", "VOICE_DRAFT_READY", "voice:realize", factual_identity, draft_identity, "VOICE", str(draft["voice_status"]), observed_at, rows)
        state = "VOICE_DRAFT_READY"
    if state != "VOICE_DRAFT_READY":
        raise VoiceBoundaryError(f"workflow is not VOICE-ready: {state}")


def _transition(store, workflow, left, right, operation, input_identity, output_identity, actor, outcome, observed_at, before_commit=None):
    semantic = {"workflow": workflow, "left": left, "right": right, "operation": operation, "input": input_identity, "output": output_identity, "actor": actor, "outcome": outcome}
    identity = object_identity(semantic)
    store.transition(
        TransitionRequest(workflow, operation, left, right, actor, outcome, input_identity, output_identity, f"attempt:{identity}", f"idempotency:{identity}", observed_at, {"component": "VNext Canonical VOICE & Chief-Editor Integration Vertical Slice v1"}),
        before_commit=before_commit,
    )
