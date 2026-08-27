from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from test_voice_production_materialization_v2 import _context

from pastila_scout.expression_catalog_v2 import (
    CommentaryRelationBindingV1,
    ExpressionOwnerSelectionReceiptV1,
    ExpressionSelectionKindV1,
    RelationAtomRoleV1,
    evaluate_expression_eligibility_v1,
    finalize_expression_selection_receipt,
    finalize_relation_binding_identity,
    load_expression_catalog_overlay_v2,
)
from pastila_scout.expression_catalog_v2.eligibility import (
    ExpressionEligibilityIntegrityError,
)
from pastila_scout.expression_retrieval_v1.catalog import load_catalog_v1
from pastila_scout.voice_executor_v2 import (
    RENDERER_IDENTITY,
    OrdinaryStoryProofExpressionActivationAuthorityV1,
    finalize_proof_expression_authority_v1,
    materialize_proof_only_ordinary_story_ir_v1_1,
    reject_as_production_authority,
    verify_and_render_proof_only_ordinary_story_ir_v1_1,
    verify_proof_expression_authority_v1,
)
from pastila_scout.voice_fact_atoms_v2.persistence import canonical_identity

ZERO = "sha256:" + "0" * 64


def _proof_context():
    values = _context("FII_BOUNDED_SERVICE_WORKFLOW_V1")
    binding, bundle, eligibility, selection, snapshot, roles, claim = values
    overlay = load_expression_catalog_overlay_v2()
    catalog = load_catalog_v1(use_cache=False)
    expression_id = "ro-expression-v1:1068794b4bf34c8914dc"
    record = next(x for x in overlay.records if x.expression_id == expression_id)
    role_names = tuple(record.adjudicated_scope.required_atoms)
    atom_ids = tuple(atom.atom_id for atom in bundle.atoms[: len(role_names)])
    relation = finalize_relation_binding_identity(
        CommentaryRelationBindingV1(
            fact_atom_bundle_identity=bundle.bundle_identity,
            relationship="SUPPORTED_OBVIOUS_BLUNDER_OR_FAILED_EXECUTION",
            atom_roles=tuple(
                RelationAtomRoleV1(role=role, atom_ids=(atom_id,))
                for role, atom_id in zip(role_names, atom_ids, strict=True)
            ),
            satisfied_constraint_codes=tuple(
                sorted(
                    record.adjudicated_scope.prohibited_binding.removeprefix(
                        "fail_closed_unless_all_constraints:"
                    ).split(",")
                )
            ),
            compatible_program_ids=("FII_BOUNDED_SERVICE_WORKFLOW_V1",),
            adjudication_receipt_identity="sha256:" + "2" * 64,
            owner_or_editor_identity="owner",
            binding_identity=ZERO,
        )
    )
    expression_result = evaluate_expression_eligibility_v1(
        bundle=bundle,
        bindings=(relation,),
        program_result=eligibility,
        selected_program_candidate=eligibility.shortlist[0],
        repetition_snapshot=snapshot,
        overlay=overlay,
        catalog=catalog,
    )
    candidate = next(
        x for x in expression_result.shortlist if x.expression_id == expression_id
    )
    expression_selection = finalize_expression_selection_receipt(
        ExpressionOwnerSelectionReceiptV1(
            fact_atom_bundle_identity=bundle.bundle_identity,
            expression_eligibility_result_identity=expression_result.result_identity,
            repetition_snapshot_identity=snapshot.snapshot_identity,
            shortlist_candidate_ids=tuple(
                x.candidate_id for x in expression_result.shortlist
            ),
            selection_kind=ExpressionSelectionKindV1.EXPRESSION,
            selected_candidate_id=candidate.candidate_id,
            selector_identity="owner",
            selected_at=datetime(2026, 8, 24, tzinfo=UTC),
            receipt_identity=ZERO,
        ),
        result=expression_result,
        snapshot=snapshot,
    )
    authority = finalize_proof_expression_authority_v1(
        OrdinaryStoryProofExpressionActivationAuthorityV1(
            proof_case_identity="TEST-ONLY-EEUP",
            proof_corpus_identity="sha256:" + "3" * 64,
            event_id=binding.event_id,
            semantic_draft_revision_identity=binding.semantic_draft_revision_identity,
            story_state_identity="sha256:" + "4" * 64,
            fact_atom_bundle_identity=bundle.bundle_identity,
            mechanic_claim_identity=claim.claim_identity,
            program_eligibility_identity=eligibility.result_identity,
            program_selection_receipt_identity=selection.receipt_identity,
            selected_program_id="FII_BOUNDED_SERVICE_WORKFLOW_V1",
            selected_program_candidate_identity=selection.selected_candidate_id,
            expression_eligibility_identity=expression_result.result_identity,
            expression_filter_evidence_identity=expression_result.result_identity,
            expression_selection_receipt_identity=expression_selection.receipt_identity,
            selected_expression_candidate_identity=candidate.candidate_id,
            expression_identity=candidate.expression_id,
            expression_scope_identity=record.adjudicated_scope.scope_identity,
            expression_surface_identity=candidate.surface_id,
            catalog_overlay_identity=overlay.overlay_identity,
            repetition_snapshot_identity=snapshot.snapshot_identity,
            relation_binding_identity=relation.binding_identity,
            renderer_identity=RENDERER_IDENTITY,
        )
    )
    kwargs = {
        "authority": authority,
        "story_state_identity": "sha256:" + "4" * 64,
        "story_binding": binding,
        "bundle": bundle,
        "eligibility": eligibility,
        "mechanic_claim": claim,
        "selection": selection,
        "repetition_snapshot": snapshot,
        "atom_roles": roles,
        "expression_eligibility": expression_result,
        "expression_selection": expression_selection,
        "relation_bindings": (relation,),
        "catalog_overlay": overlay,
        "renderer_identity": RENDERER_IDENTITY,
    }
    return authority, kwargs


def test_exact_proof_expression_tuple_materializes_and_renders():
    authority, kwargs = _proof_context()
    ir = materialize_proof_only_ordinary_story_ir_v1_1(**kwargs)
    result = verify_and_render_proof_only_ordinary_story_ir_v1_1(ir=ir, **kwargs)
    assert verify_proof_expression_authority_v1(authority) == authority
    assert ir.proof_only and not ir.production_eligible
    assert result.commentary_bytes.endswith("Și uite așa o dai de oaie.".encode())
    assert result.provenance[-1].expression_binding is not None
    assert result.provenance[0].start == 0
    assert result.provenance[-1].end == len(result.commentary_bytes.decode())
    assert result.model_calls == result.provider_calls == result.model_loads == 0


def test_authority_is_canonical_round_trip_and_unknown_version_fails():
    authority, _ = _proof_context()
    assert authority == type(authority).model_validate_json(authority.model_dump_json())
    with pytest.raises(ValidationError):
        type(authority).model_validate(
            {**authority.model_dump(mode="json"), "schema_version": "2"}
        )
    with pytest.raises(ValueError, match="identity mismatch"):
        verify_proof_expression_authority_v1(
            authority.model_copy(update={"story_state_identity": "sha256:" + "9" * 64})
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("story_state_identity", "sha256:" + "8" * 64),
        ("expression_surface_identity", "OTHER_SURFACE"),
        ("catalog_overlay_identity", "8" * 64),
        ("repetition_snapshot_identity", "sha256:" + "8" * 64),
        ("expression_filter_evidence_identity", "sha256:" + "8" * 64),
    ],
)
def test_tuple_substitution_fails_closed(field, value):
    authority, kwargs = _proof_context()
    changed = finalize_proof_expression_authority_v1(
        authority.model_copy(update={field: value, "authority_identity": ZERO})
    )
    with pytest.raises(
        ExpressionEligibilityIntegrityError, match="stale proof expression binding"
    ):
        materialize_proof_only_ordinary_story_ir_v1_1(
            **{**kwargs, "authority": changed}
        )


def test_proof_authority_is_rejected_as_production_authority():
    authority, _ = _proof_context()
    with pytest.raises(TypeError, match="not production authority"):
        reject_as_production_authority(authority)


def test_none_and_automatic_fallback_are_not_accepted():
    authority, kwargs = _proof_context()
    selection = kwargs["expression_selection"].model_copy(
        update={
            "selection_kind": ExpressionSelectionKindV1.NONE,
            "selected_candidate_id": None,
            "receipt_identity": canonical_identity("invalid-test-none"),
        }
    )
    with pytest.raises(
        ExpressionEligibilityIntegrityError, match="requires a selected expression"
    ):
        materialize_proof_only_ordinary_story_ir_v1_1(
            **{**kwargs, "authority": authority, "expression_selection": selection}
        )
