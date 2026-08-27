"""Proof-only expression activation and ordinary-story materialization."""

from __future__ import annotations

import hashlib

from pastila_scout.expression_catalog_v2.eligibility import (
    ExpressionEligibilityIntegrityError,
    finalize_expression_selection_receipt,
)
from pastila_scout.expression_catalog_v2.eligibility_models import (
    ExpressionSelectionKindV1,
)
from pastila_scout.voice_deterministic_v2.models import (
    ExpressionSpanBindingV1,
    IRSpanV1,
    ProofOnlyOrdinaryStoryAcidCommentaryIRV1_1,
    ProvenanceClassV1,
)
from pastila_scout.voice_deterministic_v2.production import (
    materialize_production_ir_v1_1,
)
from pastila_scout.voice_deterministic_v2.renderer import (
    _render_spans,
    canonical_ir_bytes,
)
from pastila_scout.voice_fact_atoms_v2.persistence import canonical_identity

from .models import OrdinaryStoryProofExpressionActivationAuthorityV1

EXPRESSION_SEPARATOR_V1 = "\n\n"
EXPRESSION_SEPARATOR_IDENTITY_V1 = "FORMAT_DOUBLE_NEWLINE_V1"


def finalize_proof_expression_authority_v1(authority):
    payload = authority.model_dump(mode="json", exclude={"authority_identity"})
    return authority.model_copy(
        update={"authority_identity": canonical_identity(payload)}
    )


def verify_proof_expression_authority_v1(authority):
    expected = finalize_proof_expression_authority_v1(authority)
    if authority.authority_identity != expected.authority_identity:
        raise ValueError("proof expression authority identity mismatch")
    return authority


def reject_proof_expression_authority_as_production(authority: object) -> None:
    if isinstance(authority, OrdinaryStoryProofExpressionActivationAuthorityV1):
        raise TypeError("proof-only expression authority is not production authority")


def materialize_proof_only_ordinary_story_ir_v1_1(
    *,
    authority,
    story_state_identity,
    story_binding,
    bundle,
    eligibility,
    mechanic_claim,
    selection,
    repetition_snapshot,
    atom_roles,
    expression_eligibility,
    expression_selection,
    relation_bindings,
    catalog_overlay,
    renderer_identity,
):
    verify_proof_expression_authority_v1(authority)
    if expression_selection.selection_kind is not ExpressionSelectionKindV1.EXPRESSION:
        raise ExpressionEligibilityIntegrityError(
            "proof expression activation requires a selected expression"
        )
    finalized = finalize_expression_selection_receipt(
        expression_selection,
        result=expression_eligibility,
        snapshot=repetition_snapshot,
    )
    if finalized != expression_selection:
        raise ExpressionEligibilityIntegrityError(
            "expression selection receipt is not finalized"
        )
    candidate = next(
        (
            x
            for x in expression_eligibility.shortlist
            if x.candidate_id == expression_selection.selected_candidate_id
        ),
        None,
    )
    if candidate is None:
        raise ExpressionEligibilityIntegrityError("selected expression is unavailable")
    binding = next(
        (
            x
            for x in relation_bindings
            if x.binding_identity == candidate.relation_binding_identity
        ),
        None,
    )
    records = {x.expression_id: x for x in catalog_overlay.records}
    surfaces = {x.surface_id: x for x in catalog_overlay.approved_surfaces}
    record = records.get(candidate.expression_id)
    surface = surfaces.get(candidate.surface_id)
    if (
        record is None
        or surface is None
        or record.adjudication_status.value != "approved_candidate_scope"
    ):
        raise ExpressionEligibilityIntegrityError(
            "selected Catalog scope or surface is not approved"
        )
    scope_identity = record.adjudicated_scope.scope_identity
    checks = {
        "event_id": story_binding.event_id,
        "semantic_draft_revision_identity": story_binding.semantic_draft_revision_identity,
        "story_state_identity": story_state_identity,
        "fact_atom_bundle_identity": bundle.bundle_identity,
        "mechanic_claim_identity": mechanic_claim.claim_identity,
        "program_eligibility_identity": eligibility.result_identity,
        "program_selection_receipt_identity": selection.receipt_identity,
        "selected_program_id": next(
            x.program_id
            for x in eligibility.shortlist
            if x.candidate_id == selection.selected_candidate_id
        ),
        "selected_program_candidate_identity": selection.selected_candidate_id,
        "expression_eligibility_identity": expression_eligibility.result_identity,
        "expression_filter_evidence_identity": expression_eligibility.result_identity,
        "expression_selection_receipt_identity": expression_selection.receipt_identity,
        "selected_expression_candidate_identity": candidate.candidate_id,
        "expression_identity": candidate.expression_id,
        "expression_scope_identity": scope_identity,
        "expression_surface_identity": candidate.surface_id,
        "catalog_overlay_identity": catalog_overlay.overlay_identity,
        "repetition_snapshot_identity": repetition_snapshot.snapshot_identity,
        "relation_binding_identity": candidate.relation_binding_identity,
        "renderer_identity": renderer_identity,
    }
    for name, value in checks.items():
        if getattr(authority, name) != value:
            raise ExpressionEligibilityIntegrityError(
                f"stale proof expression binding: {name}"
            )
    if (
        binding is None
        or candidate.exact_surface != surface.exact_surface
        or candidate.surface_utf8_sha256 != surface.surface_utf8_sha256
    ):
        raise ExpressionEligibilityIntegrityError(
            "selected expression provenance mismatch"
        )
    base = materialize_production_ir_v1_1(
        story_binding=story_binding,
        bundle=bundle,
        eligibility=eligibility,
        mechanic_claim=mechanic_claim,
        selection=selection,
        repetition_snapshot=repetition_snapshot,
        atom_roles=atom_roles,
        activation_policy_identity="sha256:" + "0" * 64,
        renderer_identity=renderer_identity,
        relationship_binding_identities=tuple(
            x.binding_identity for x in relation_bindings
        ),
    )
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
        owner_selection_receipt_identity=expression_selection.receipt_identity,
        repetition_snapshot_identity=repetition_snapshot.snapshot_identity,
        repetition_identity=candidate.repetition_identity,
        character_provenance_identity=provenance_identity,
    )
    spans = base.spans + (
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
    output = "".join(x.text for x in spans).encode("utf-8")
    return ProofOnlyOrdinaryStoryAcidCommentaryIRV1_1(
        proof_expression_authority_identity=authority.authority_identity,
        semantic_draft_revision_identity=base.semantic_draft_revision_identity,
        event_id=base.event_id,
        story_position=base.story_position,
        fact_atom_bundle_identity=base.fact_atom_bundle_identity,
        mechanic_id=base.mechanic_id,
        mechanic_eligibility_claim_identity=base.mechanic_eligibility_claim_identity,
        realization_program_id=base.realization_program_id,
        realization_program_sha256=base.realization_program_sha256,
        program_eligibility_identity=base.program_eligibility_identity,
        program_selection_receipt_identity=base.program_selection_receipt_identity,
        selected_program_candidate_identity=base.selected_program_candidate_identity,
        atom_role_bindings=base.atom_role_bindings,
        relationship_binding_identities=base.relationship_binding_identities,
        expression_eligibility_identity=expression_eligibility.result_identity,
        expression_selection_receipt_identity=expression_selection.receipt_identity,
        repetition_snapshot_identity=base.repetition_snapshot_identity,
        catalog_overlay_identity=catalog_overlay.overlay_identity,
        renderer_identity=renderer_identity,
        spans=spans,
        repetition_signature=base.repetition_signature,
        expected_output_sha256=hashlib.sha256(output).hexdigest(),
    )


def verify_and_render_proof_only_ordinary_story_ir_v1_1(*, ir, **governed_inputs):
    """Reconstruct the exact governed IR, then render with full provenance."""

    expected = materialize_proof_only_ordinary_story_ir_v1_1(**governed_inputs)
    if canonical_ir_bytes(expected) != canonical_ir_bytes(ir):
        raise ExpressionEligibilityIntegrityError(
            "proof-only expression IR differs from governed materialization"
        )
    return _render_spans(ir)


__all__ = [
    "finalize_proof_expression_authority_v1",
    "materialize_proof_only_ordinary_story_ir_v1_1",
    "reject_proof_expression_authority_as_production",
    "verify_and_render_proof_only_ordinary_story_ir_v1_1",
    "verify_proof_expression_authority_v1",
]
