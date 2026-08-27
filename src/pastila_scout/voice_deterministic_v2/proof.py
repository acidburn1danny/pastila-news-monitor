"""Repository-only construction helpers for the frozen eight-case proof."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pastila_scout.voice_deterministic_v2.library import FROZEN_PROOF_CASES_V1
from pastila_scout.voice_deterministic_v2.models import (
    AcidCommentaryIRV1_1,
    FictionalRoleplayActorV1,
    IRDispositionV1,
    IRSpanV1,
    ProvenanceClassV1,
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _classify(raw_class: str) -> ProvenanceClassV1:
    if raw_class == "AUTHORIZED_EVENT_FACT_ATOM":
        return ProvenanceClassV1.AUTHORIZED_EVENT_FACT_ATOM
    if raw_class == "AUTHORIZED_BACKGROUND_FACT_ATOM":
        return ProvenanceClassV1.AUTHORIZED_BACKGROUND_FACT_ATOM
    if raw_class == "NONFACTUAL_COMIC_SURFACE":
        return ProvenanceClassV1.NONFACTUAL_COMIC_SURFACE
    if raw_class == "NONLITERAL_SUPPORTED_FACT_PARAPHRASE":
        return ProvenanceClassV1.NONLITERAL_SUPPORTED_FACT_PARAPHRASE
    return ProvenanceClassV1.DETERMINISTIC_FORMATTING_OR_OPERATOR


def _line_lookup(program: dict[str, Any]) -> dict[int, dict[str, Any]]:
    lookup: dict[int, dict[str, Any]] = {}
    for entry in program["character_provenance"]["line_defaults"]:
        raw_lines = entry["lines"]
        if len(raw_lines) == 2 and raw_lines[1] > raw_lines[0] + 1:
            lines = range(raw_lines[0], raw_lines[1] + 1)
        else:
            lines = raw_lines
        for line in lines:
            if line in lookup:
                raise ValueError(f"overlapping provenance on line {line}")
            lookup[line] = entry
    return lookup


def _actor_for_line(program: dict[str, Any], line: int) -> str | None:
    for actor in program.get("fictional_roleplay_actors", []):
        span = actor["explicit_frame_span"]
        if span["start_line"] <= line <= span["end_line"]:
            return actor["fictional_actor_id"]
    return None


def _actors(program: dict[str, Any]) -> tuple[FictionalRoleplayActorV1, ...]:
    actors: list[FictionalRoleplayActorV1] = []
    for raw in program.get("fictional_roleplay_actors", []):
        span = raw["explicit_frame_span"]
        termination = raw["frame_termination_span"]
        termination_text = (
            termination["kind"]
            if "kind" in termination
            else f"lines:{termination['start_line']}-{termination['end_line']}"
        )
        actors.append(
            FictionalRoleplayActorV1(
                fictional_actor_id=raw["fictional_actor_id"],
                fictional_role=raw["fictional_role"],
                explicit_frame_span=f"lines:{span['start_line']}-{span['end_line']}",
                identity_isolation_from_event_actor_ids=tuple(
                    raw["identity_isolation_from_event_actors"]
                ),
                allowed_invented_dialogue=raw["allowed_invented_dialogue"],
                allowed_invented_internal_state=raw["allowed_invented_internal_state"],
                allowed_invented_fictional_history=raw[
                    "allowed_invented_fictional_history"
                ],
                professional_domain_premise_atom_ids=tuple(
                    raw["professional_domain_premise_atom_ids"]
                ),
                explicit_frame_termination=termination_text,
            )
        )
    return tuple(actors)


def build_frozen_realization_ir(
    proof_id: str, evidence_root: Path
) -> AcidCommentaryIRV1_1:
    """Build P1-P6 from hash-verified frozen owner evidence."""

    case = FROZEN_PROOF_CASES_V1[proof_id]
    if not case.expected_output_sha256 or not case.realization_program_sha256:
        raise ValueError("proof case is not a realization")
    case_dir = evidence_root / proof_id
    manifest = json.loads((case_dir / "manifest.json").read_text(encoding="utf-8"))
    target_path = case_dir / manifest["target"]["path"]
    program_path = case_dir / manifest["realization_program"]["path"]
    target_bytes = target_path.read_bytes()
    program_bytes = program_path.read_bytes()
    if _sha256(target_bytes) != case.expected_output_sha256:
        raise ValueError("frozen owner target hash mismatch")
    if _sha256(program_bytes) != case.realization_program_sha256:
        raise ValueError("frozen realization-program hash mismatch")

    program = json.loads(program_bytes.decode("utf-8"))
    lookup = _line_lookup(program)
    spans: list[IRSpanV1] = []
    for line_no, full_line in enumerate(
        target_bytes.decode("utf-8").splitlines(keepends=True), start=1
    ):
        if full_line.endswith("\r\n"):
            body, ending = full_line[:-2], "\r\n"
        elif full_line.endswith("\n"):
            body, ending = full_line[:-1], "\n"
        else:
            body, ending = full_line, ""
        if body:
            entry = lookup.get(line_no)
            if entry is None:
                raise ValueError(f"unclassified authored characters on line {line_no}")
            source = str(entry.get("source", "APPROVED_OPERATOR"))
            mapping = entry.get("mapping")
            if mapping is None and "PROOF_SPECIFIC_KICK_PARAPHRASE" in source:
                mapping = "P2_PROOF_SPECIFIC_KICK_PARAPHRASE_BOUND_TO_P2-EF-02"
            callback = (
                source if source.startswith(("CALLBACK_", "Q9-CALLBACK")) else None
            )
            spans.append(
                IRSpanV1(
                    text=body,
                    provenance_class=_classify(entry["class"]),
                    source_identity=source,
                    fictional_actor_id=_actor_for_line(program, line_no),
                    nonliteral_mapping_id=mapping,
                    callback_id=callback,
                )
            )
        if ending:
            spans.append(
                IRSpanV1(
                    text=ending,
                    provenance_class=(
                        ProvenanceClassV1.DETERMINISTIC_FORMATTING_OR_OPERATOR
                    ),
                    source_identity="DETERMINISTIC_LINE_ENDING",
                    fictional_actor_id=_actor_for_line(program, line_no),
                )
            )

    return AcidCommentaryIRV1_1(
        proof_id=proof_id,
        source_record_id=case.source_record_id,
        realization_program_id=case.realization_program_id,
        realization_program_sha256=case.realization_program_sha256,
        mechanic_id=case.mechanic_id,
        disposition=IRDispositionV1.REALIZE,
        spans=tuple(spans),
        fictional_actors=_actors(program),
        repetition_signature=case.repetition_signature,
        expected_output_sha256=case.expected_output_sha256,
    )


def build_p7_authority_abstention_ir() -> AcidCommentaryIRV1_1:
    case = FROZEN_PROOF_CASES_V1["P7"]
    return AcidCommentaryIRV1_1(
        proof_id=case.proof_id,
        source_record_id=case.source_record_id,
        realization_program_id=case.realization_program_id,
        realization_program_sha256=_sha256(case.realization_program_id.encode()),
        mechanic_id=case.mechanic_id,
        disposition=IRDispositionV1.ABSTAIN,
        repetition_signature=case.repetition_signature,
        abstention_reason=case.expected_abstention_reason,
    )


def build_p8_repetition_abstention_ir(
    *, exhausted_signatures: frozenset[str]
) -> AcidCommentaryIRV1_1:
    case = FROZEN_PROOF_CASES_V1["P8"]
    if case.repetition_signature not in exhausted_signatures:
        raise ValueError("P8 repetition budget is not exhausted")
    return AcidCommentaryIRV1_1(
        proof_id=case.proof_id,
        source_record_id=case.source_record_id,
        realization_program_id=case.realization_program_id,
        realization_program_sha256=_sha256(case.realization_program_id.encode()),
        mechanic_id=case.mechanic_id,
        disposition=IRDispositionV1.ABSTAIN,
        repetition_signature=case.repetition_signature,
        abstention_reason=case.expected_abstention_reason,
    )


__all__ = [
    "build_frozen_realization_ir",
    "build_p7_authority_abstention_ir",
    "build_p8_repetition_abstention_ir",
]
