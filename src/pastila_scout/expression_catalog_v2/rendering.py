"""Governed expression selection-to-IR integration for deterministic Voice proofs."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError

from pastila_scout.voice_deterministic_v2.models import (
    AcidCommentaryIRV1_1,
    DeterministicVoiceResultV1,
    ExpressionSpanBindingV1,
    IRSpanV1,
    ProvenanceClassV1,
)
from pastila_scout.voice_deterministic_v2.renderer import (
    DeterministicVoiceValidationError,
    _render_deterministic_voice_v2,
    canonical_ir_bytes,
    render_deterministic_voice_v2,
)
from pastila_scout.voice_eligibility_v2 import VoiceRepetitionSnapshotV1
from pastila_scout.voice_fact_atoms_v2.persistence import (
    canonical_bytes,
    canonical_identity,
)

from .eligibility import (
    ExpressionEligibilityIntegrityError,
    _sealed,
    finalize_expression_selection_receipt,
)
from .eligibility_models import (
    CommentaryRelationBinding,
    ExpressionEligibilityResultV1,
    ExpressionOwnerSelectionReceiptV1,
    ExpressionSelectionKindV1,
)
from .models import FrozenModel

EXPRESSION_SEPARATOR_V1 = "\n\n"
EXPRESSION_SEPARATOR_IDENTITY_V1 = "VOICE_EXPRESSION_SEPARATOR_DOUBLE_NEWLINE_V1"


class IntegratedExpressionProofArtifactV1(FrozenModel):
    schema_name: Literal["pastilaacida-integrated-expression-proof"] = (
        "pastilaacida-integrated-expression-proof"
    )
    schema_version: Literal["1"] = "1"
    ir: AcidCommentaryIRV1_1
    result: DeterministicVoiceResultV1
    selection_receipt: ExpressionOwnerSelectionReceiptV1
    eligibility_result_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    artifact_identity: str = Field(
        default="sha256:" + "0" * 64, pattern=r"^sha256:[0-9a-f]{64}$"
    )


class IntegratedExpressionProofStoreV1:
    def __init__(self, path: Path):
        self.path = path

    def save(self, artifact: IntegratedExpressionProofArtifactV1) -> None:
        if artifact.artifact_identity != _sealed(artifact, "artifact_identity"):
            raise ExpressionEligibilityIntegrityError("artifact identity mismatch")
        raw = canonical_bytes(artifact)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with temporary.open("wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def load(self) -> IntegratedExpressionProofArtifactV1:
        raw = self.path.read_bytes()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExpressionEligibilityIntegrityError(
                "invalid proof artifact JSON"
            ) from exc
        if (
            not isinstance(payload, dict)
            or payload.get("schema_name") != "pastilaacida-integrated-expression-proof"
            or payload.get("schema_version") != "1"
        ):
            raise ExpressionEligibilityIntegrityError(
                "unsupported integrated proof artifact version"
            )
        try:
            artifact = IntegratedExpressionProofArtifactV1.model_validate(payload)
        except ValidationError as exc:
            raise ExpressionEligibilityIntegrityError(
                "invalid integrated proof artifact"
            ) from exc
        if canonical_bytes(artifact) != raw:
            raise ExpressionEligibilityIntegrityError(
                "integrated proof artifact is not canonical"
            )
        if artifact.artifact_identity != _sealed(artifact, "artifact_identity"):
            raise ExpressionEligibilityIntegrityError("artifact identity mismatch")
        return artifact


def _selected_candidate(result, receipt):
    if receipt.selection_kind is ExpressionSelectionKindV1.NONE:
        return None
    return next(
        (
            item
            for item in result.shortlist
            if item.candidate_id == receipt.selected_candidate_id
        ),
        None,
    )


def integrate_expression_selection_v1(
    *,
    base_ir: AcidCommentaryIRV1_1,
    eligibility_result: ExpressionEligibilityResultV1,
    selection_receipt: ExpressionOwnerSelectionReceiptV1,
    relation_bindings: tuple[CommentaryRelationBinding, ...],
    repetition_snapshot: VoiceRepetitionSnapshotV1,
) -> AcidCommentaryIRV1_1:
    """Append exactly one selected closed surface, or preserve the base IR for NONE."""

    render_deterministic_voice_v2(base_ir)
    finalized = finalize_expression_selection_receipt(
        selection_receipt,
        result=eligibility_result,
        snapshot=repetition_snapshot,
    )
    if finalized != selection_receipt:
        raise ExpressionEligibilityIntegrityError("selection receipt is not finalized")
    if selection_receipt.selection_kind is ExpressionSelectionKindV1.NONE:
        return base_ir

    candidate = _selected_candidate(eligibility_result, selection_receipt)
    if candidate is None:
        raise ExpressionEligibilityIntegrityError("selected candidate is unavailable")
    binding = next(
        (
            item
            for item in relation_bindings
            if item.binding_identity == candidate.relation_binding_identity
        ),
        None,
    )
    if binding is None or binding.binding_identity != _sealed(
        binding, "binding_identity"
    ):
        raise ExpressionEligibilityIntegrityError(
            "selected relation binding is invalid"
        )
    if binding.insertion_point != candidate.insertion_point:
        raise ExpressionEligibilityIntegrityError("expression placement mismatch")
    if hashlib.sha256(candidate.exact_surface.encode("utf-8")).hexdigest() != (
        candidate.surface_utf8_sha256
    ):
        raise ExpressionEligibilityIntegrityError("selected surface hash mismatch")

    provenance_identity = canonical_identity(
        {
            "expression_id": candidate.expression_id,
            "surface_id": candidate.surface_id,
            "surface_utf8_sha256": candidate.surface_utf8_sha256,
            "relationship_binding_identity": binding.binding_identity,
        }
    )
    expression_binding = ExpressionSpanBindingV1(
        catalog_expression_id=candidate.expression_id,
        selected_surface_id=candidate.surface_id,
        selected_surface_utf8_sha256=candidate.surface_utf8_sha256,
        relationship_binding_identity=binding.binding_identity,
        pool_identity=candidate.pool_identity,
        selected_program_candidate_id=candidate.selected_program_candidate_id,
        owner_selection_receipt_identity=selection_receipt.receipt_identity,
        repetition_snapshot_identity=repetition_snapshot.snapshot_identity,
        repetition_identity=candidate.repetition_identity,
        character_provenance_identity=provenance_identity,
    )
    spans = base_ir.spans + (
        IRSpanV1(
            text=EXPRESSION_SEPARATOR_V1,
            provenance_class=ProvenanceClassV1.DETERMINISTIC_FORMATTING_OR_OPERATOR,
            source_identity=EXPRESSION_SEPARATOR_IDENTITY_V1,
        ),
        IRSpanV1(
            text=candidate.exact_surface,
            provenance_class=ProvenanceClassV1.APPROVED_EXPRESSION_SURFACE,
            source_identity=candidate.surface_id,
            expression_binding=expression_binding,
        ),
    )
    expected = hashlib.sha256("".join(item.text for item in spans).encode("utf-8"))
    return base_ir.model_copy(
        update={
            "spans": spans,
            "expected_output_sha256": expected.hexdigest(),
            "base_span_count": len(base_ir.spans),
            "base_output_sha256": base_ir.expected_output_sha256,
        }
    )


def render_integrated_expression_v1(
    *,
    ir: AcidCommentaryIRV1_1,
    eligibility_result: ExpressionEligibilityResultV1,
    selection_receipt: ExpressionOwnerSelectionReceiptV1,
    relation_bindings: tuple[CommentaryRelationBinding, ...],
    repetition_snapshot: VoiceRepetitionSnapshotV1,
) -> DeterministicVoiceResultV1:
    """Validate every governed identity before rendering an expression span."""

    expected_ir = integrate_expression_selection_v1(
        base_ir=ir.model_copy(
            update={
                "spans": ir.spans[: ir.base_span_count],
                "expected_output_sha256": ir.base_output_sha256,
                "base_span_count": None,
                "base_output_sha256": None,
            }
        )
        if ir.base_span_count is not None
        else ir,
        eligibility_result=eligibility_result,
        selection_receipt=selection_receipt,
        relation_bindings=relation_bindings,
        repetition_snapshot=repetition_snapshot,
    )
    if canonical_ir_bytes(expected_ir) != canonical_ir_bytes(ir):
        raise DeterministicVoiceValidationError(
            "integrated expression IR does not match governed selection"
        )
    return _render_deterministic_voice_v2(ir, expression_context_validated=True)


def finalize_integrated_expression_artifact_v1(
    artifact: IntegratedExpressionProofArtifactV1,
) -> IntegratedExpressionProofArtifactV1:
    return artifact.model_copy(
        update={"artifact_identity": _sealed(artifact, "artifact_identity")}
    )


__all__ = [
    "IntegratedExpressionProofArtifactV1",
    "IntegratedExpressionProofStoreV1",
    "finalize_integrated_expression_artifact_v1",
    "integrate_expression_selection_v1",
    "render_integrated_expression_v1",
]
