"""Durable host/runner payload binding for the approved V2 projector; no execution."""
from __future__ import annotations

import hashlib
import json
from dataclasses import fields
from pathlib import Path
from typing import Iterable, Mapping

from .stage_p_construction_obligation_projector_binding_v1 import (
    APPROVED_PROJECTOR_IDENTITY,
    EvaluatorProjectorPreparationV1,
    ProjectorSourceBindingEnvelopeV1,
    StagePConstructionObligationProjectorRunnerInterfaceV1,
)


PAYLOAD_SCHEMA = "pastila-semantic-admission-v2-stage-p-projector-runner-payload"
PAYLOAD_VERSION = "2.0.0-evaluation.1"
APPROVED_INTERFACE_BINDING_IDENTITY = "56701585d482975842f712dee77aa5d775567c4a79d320c252a43d53a51df45b"
DEPENDENCY_IDENTITIES = {
    Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_projector_binding_v1.py"):
        "8da4dbf3575cbdc93f8fe9474ef23902f0b0eab45263d260076b8e026a7bb501",
    Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_token_projector_v1.py"):
        "0fdd777f5c2f9305279a8a3a8cb69cfcae86b818e403abe43b495dbe43503221",
    Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_character_controller_v1.py"):
        "7bd33b6ed6004addd264574b545308ddd00f8913c623a4d9dce7eff6d33522fe",
    Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_incremental_tracker_v2.py"):
        "0a512731e39a8e7e872ae76ac99dd5370c8816387dfb3284d0af4b487e2e0b2d",
    Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_constraint_v2.py"):
        "b9d1e78ed1a2c0861d671159e2aba89c2d0d80e9df277ad71bb177f8eeb4e520",
}


class DurableConstructionObligationProjectorPayloadBinderV2:
    """Verify host dependencies and construct the exact runner payload bytes."""

    def __init__(self, *, project_root: Path, max_new_tokens: int = 3200) -> None:
        self.project_root = project_root.resolve(strict=True)
        if type(max_new_tokens) is not int or max_new_tokens <= 0:
            raise ValueError("PROJECTOR_PAYLOAD_TOKEN_LIMIT_INVALID")
        self.max_new_tokens = max_new_tokens
        for relative, expected in DEPENDENCY_IDENTITIES.items():
            target = self.project_root / relative
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                raise RuntimeError(f"PROJECTOR_PAYLOAD_DEPENDENCY_DRIFT:{relative.as_posix()}")

    def build(self, preparation: EvaluatorProjectorPreparationV1) -> bytes:
        if type(preparation) is not EvaluatorProjectorPreparationV1:
            raise TypeError("PROJECTOR_PREPARATION_EXACT_TYPE_REQUIRED")
        envelope = preparation.source_binding
        value = {
            "schema_name": PAYLOAD_SCHEMA, "schema_version": PAYLOAD_VERSION,
            "interface_binding_identity": APPROVED_INTERFACE_BINDING_IDENTITY,
            "projector_identity": APPROVED_PROJECTOR_IDENTITY,
            "prompt": preparation.rendered_prompt,
            "max_new_tokens": self.max_new_tokens,
            "source_binding": {field.name: getattr(envelope, field.name) for field in fields(envelope)},
        }
        return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                           allow_nan=False) + "\n").encode("utf-8")


class ConstructionObligationProjectorRunnerPayloadV2:
    """Strict runner-side payload parser and projector constructor."""

    def __init__(self, *, raw_payload: bytes) -> None:
        try:
            value = json.loads(raw_payload.decode("utf-8", errors="strict"))
        except Exception as error:
            raise ValueError("PROJECTOR_PAYLOAD_JSON_INVALID") from error
        required = {"schema_name", "schema_version", "interface_binding_identity",
                    "projector_identity", "prompt", "max_new_tokens", "source_binding"}
        if type(value) is not dict or set(value) != required:
            raise ValueError("PROJECTOR_PAYLOAD_SHAPE_INVALID")
        if (value["schema_name"] != PAYLOAD_SCHEMA or value["schema_version"] != PAYLOAD_VERSION or
                value["interface_binding_identity"] != APPROVED_INTERFACE_BINDING_IDENTITY or
                value["projector_identity"] != APPROVED_PROJECTOR_IDENTITY):
            raise ValueError("PROJECTOR_PAYLOAD_IDENTITY_MISMATCH")
        if type(value["prompt"]) is not str or not value["prompt"]:
            raise ValueError("PROJECTOR_PAYLOAD_PROMPT_INVALID")
        if type(value["max_new_tokens"]) is not int or value["max_new_tokens"] <= 0:
            raise ValueError("PROJECTOR_PAYLOAD_TOKEN_LIMIT_INVALID")
        names = {field.name for field in fields(ProjectorSourceBindingEnvelopeV1)}
        if type(value["source_binding"]) is not dict or set(value["source_binding"]) != names:
            raise ValueError("PROJECTOR_PAYLOAD_SOURCE_BINDING_SHAPE_INVALID")
        self.prompt = value["prompt"]; self.max_new_tokens = value["max_new_tokens"]
        self.envelope = ProjectorSourceBindingEnvelopeV1(**value["source_binding"])
        self.payload_sha256 = hashlib.sha256(raw_payload).hexdigest()

    def bind_projector(self, *, token_pieces: Mapping[int, str], eos_token_id: int,
                       excluded_token_ids: Iterable[int]):
        return StagePConstructionObligationProjectorRunnerInterfaceV1.bind(
            envelope=self.envelope, token_pieces=token_pieces, eos_token_id=eos_token_id,
            excluded_token_ids=excluded_token_ids)


__all__ = (
    "ConstructionObligationProjectorRunnerPayloadV2", "DEPENDENCY_IDENTITIES",
    "DurableConstructionObligationProjectorPayloadBinderV2",
)
