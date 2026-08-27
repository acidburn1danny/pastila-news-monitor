from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from pastila_scout.expression_catalog_v2.eligibility import (
    _sealed as expression_sealed,
)
from pastila_scout.expression_catalog_v2.eligibility import (
    finalize_expression_selection_receipt,
)
from pastila_scout.expression_catalog_v2.eligibility_models import (
    ExpressionEligibilityResultV1,
    ExpressionOwnerSelectionReceiptV1,
    ExpressionSelectionKindV1,
)
from pastila_scout.voice_deterministic_v2 import (
    render_production_deterministic_voice_v2,
)
from pastila_scout.voice_deterministic_v2.production import (
    PRODUCTION_PROGRAMS_V1,
    PRODUCTION_SURFACE_BY_ID_V1,
    ProductionMaterializationError,
    materialize_production_ir_v1_1,
)
from pastila_scout.voice_eligibility_v2 import (
    ZERO_IDENTITY,
    AtomRoleBindingV1,
    MechanicEligibilityClaimV1,
    SelectionKindV1,
    VoiceOwnerSelectionReceiptV1,
    VoiceRepetitionSnapshotV1,
    evaluate_voice_eligibility_v1,
    finalize_claim_identity,
    finalize_repetition_snapshot,
    finalize_selection_receipt,
)
from pastila_scout.voice_eligibility_v2.library import PROGRAM_SPECS_V1
from pastila_scout.voice_executor_v2 import (
    RENDERER_IDENTITY,
    ZERO_ACTIVATION_POLICY_V1,
    DeterministicVoiceExecutorV2,
    build_governed_execution_request_v2,
)
from pastila_scout.voice_fact_atoms_v2 import (
    AtomKind,
    AuthorityClass,
    AuthorityPassageV1,
    CandidateKind,
    CompleteQuantityV1,
    FactAtomV1,
    SurfaceCandidateV1,
    VoiceFactAtomBundleV1,
    finalize_bundle_identity,
)
from pastila_scout.voice_workflow_v2.models import VoiceStoryBindingV1

SHA = "sha256:" + "1" * 64
ROLE_LAYOUTS = {
    "NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1": (
        ("complete_quantity", "q1"),
        ("quantity_object", "p1"),
    ),
    "NEL_ACCUMULATION_SCALE_VISUALIZATION_V1": (
        ("complete_quantity", "q1"),
        ("quantity_scope", "p1"),
    ),
    "NEL_DELAYED_QUANTITY_REVEAL_V1": (
        ("quantity_object", "p1"),
        ("complete_quantity", "q1"),
    ),
    "NEL_TWO_AXIS_QUANTITY_CONTRAST_V1": (
        ("axis_a", "q1"),
        ("axis_b", "q2"),
        ("same_event_relationship", "p1"),
    ),
    "FII_BOUNDED_INTAKE_DIALOGUE_V1": (
        ("service_or_intake_role", "p1"),
        ("supported_incongruity", "p2"),
    ),
    "FII_CLOSED_OPTION_MENU_V1": (
        ("service_or_process", "p1"),
        ("supported_outcome", "p2"),
    ),
    "FII_FICTIONAL_SERVICE_ADVERTISEMENT_V1": (
        ("service_or_process", "p1"),
        ("supported_outcome_or_limitation", "p2"),
    ),
    "FII_BOUNDED_SERVICE_WORKFLOW_V1": (
        ("start_condition", "p1"),
        ("outcome_or_status", "p2"),
    ),
    "USF_ISOLATED_SCENE_AND_EXACT_RETURN_V1": (
        ("factual_anchor", "p1"),
        ("exact_target", "b1"),
    ),
    "USF_DISTINCT_DOMAIN_ANALOGY_DETOUR_V1": (
        ("factual_anchor", "p1"),
        ("exact_target", "b1"),
    ),
    "USF_ABSURD_ALTERNATIVES_WITHOUT_SELECTION_V1": (
        ("factual_anchor", "p1"),
        ("exact_target", "b1"),
    ),
    "USF_KNOWN_UNKNOWN_LEDGER_V1": (
        ("known_anchor_a", "p1"),
        ("known_anchor_b", "p2"),
        ("exact_target", "b1"),
    ),
}


def test_production_authority_resolves_all_frozen_program_contracts():
    expected = {item.program_id: item for item in PROGRAM_SPECS_V1}
    assert len(PRODUCTION_PROGRAMS_V1) == len(expected) == 12
    for authority in PRODUCTION_PROGRAMS_V1:
        item = expected[authority.program_id]
        assert authority.mechanic_id == item.mechanic_id.value
        assert authority.boundary_requirements == item.required_boundary_codes
        assert authority.surface_ids == item.surface_ids
        assert authority.cadence_signature == item.cadence_signature
        assert authority.episode_use_ceiling == item.episode_use_ceiling


def _candidate(atom_id: str, text: str) -> SurfaceCandidateV1:
    evidence = AuthorityPassageV1(
        authority_class=AuthorityClass.EVENT,
        authority_identity=SHA,
        source_identity="source",
        passage=text,
        start=0,
        end=len(text),
    )
    return SurfaceCandidateV1(
        candidate_id=f"c-{atom_id}",
        kind=CandidateKind.EXACT_SPAN,
        evidence=evidence,
        normalized_key=text.casefold(),
        extraction_receipt_identity=SHA,
    )


def _context(program_id: str):
    texts = {
        "p1": "Faptul principal este confirmat.",
        "p2": "Rezultatul este confirmat.",
        "q1": "aproximativ 10 lei",
        "q2": "20 de cazuri",
        "b1": "Cauza nu este cunoscută.",
    }
    candidates = tuple(_candidate(key, value) for key, value in texts.items())
    evidence = {item.candidate_id[2:]: item.evidence for item in candidates}
    atoms = (
        FactAtomV1(
            atom_id="p1",
            kind=AtomKind.EVENT_PROPOSITION,
            proposition=texts["p1"],
            authority_class=AuthorityClass.EVENT,
            evidence=(evidence["p1"],),
            candidate_ids=("c-p1",),
        ),
        FactAtomV1(
            atom_id="p2",
            kind=AtomKind.EVENT_PROPOSITION,
            proposition=texts["p2"],
            authority_class=AuthorityClass.EVENT,
            evidence=(evidence["p2"],),
            candidate_ids=("c-p2",),
        ),
        FactAtomV1(
            atom_id="q1",
            kind=AtomKind.COMPLETE_QUANTITY,
            proposition=texts["q1"],
            authority_class=AuthorityClass.EVENT,
            evidence=(evidence["q1"],),
            candidate_ids=("c-q1",),
            quantity=CompleteQuantityV1(
                exact_surface=texts["q1"],
                numeric_surface="10",
                approximation="aproximativ",
                bound_semantics="approximate",
                unit_or_currency="lei",
                subject_scope="cost",
            ),
        ),
        FactAtomV1(
            atom_id="q2",
            kind=AtomKind.COMPLETE_QUANTITY,
            proposition=texts["q2"],
            authority_class=AuthorityClass.EVENT,
            evidence=(evidence["q2"],),
            candidate_ids=("c-q2",),
            quantity=CompleteQuantityV1(
                exact_surface=texts["q2"],
                numeric_surface="20",
                bound_semantics="exact",
                unit_or_currency="cazuri",
                subject_scope="cazuri",
            ),
        ),
        FactAtomV1(
            atom_id="b1",
            kind=AtomKind.CAUSAL_BOUNDARY,
            proposition=texts["b1"],
            authority_class=AuthorityClass.EVENT,
            evidence=(evidence["b1"],),
            candidate_ids=("c-b1",),
            qualification_target_atom_ids=("p1", "p2"),
        ),
    )
    bundle = finalize_bundle_identity(
        VoiceFactAtomBundleV1(
            revision=1,
            semantic_draft_revision_identity=SHA,
            event_id=1,
            story_position=1,
            factual_summary_identity=SHA,
            event_authority_identity=SHA,
            candidates=candidates,
            atoms=atoms,
            bundle_identity=ZERO_IDENTITY,
        )
    )
    spec = next(item for item in PROGRAM_SPECS_V1 if item.program_id == program_id)
    roles = tuple(
        AtomRoleBindingV1(role=role, atom_ids=(atom_id,))
        for role, atom_id in ROLE_LAYOUTS[program_id]
    )
    claim = finalize_claim_identity(
        MechanicEligibilityClaimV1(
            fact_atom_bundle_identity=bundle.bundle_identity,
            mechanic_id=spec.mechanic_id,
            atom_roles=roles,
            satisfied_boundary_codes=tuple(sorted(spec.required_boundary_codes)),
            adjudication_receipt_identity=SHA,
            claim_identity=ZERO_IDENTITY,
        )
    )
    snapshot = finalize_repetition_snapshot(
        VoiceRepetitionSnapshotV1(
            current_episode_ordinal=1,
            current_story_position=1,
            snapshot_identity=ZERO_IDENTITY,
        )
    )
    eligibility = evaluate_voice_eligibility_v1(
        bundle=bundle,
        claims=(claim,),
        repetition_snapshot=snapshot,
        requested_program_ids=(program_id,),
    )
    candidate = eligibility.shortlist[0]
    selection = finalize_selection_receipt(
        VoiceOwnerSelectionReceiptV1(
            fact_atom_bundle_identity=bundle.bundle_identity,
            eligibility_result_identity=eligibility.result_identity,
            repetition_snapshot_identity=snapshot.snapshot_identity,
            shortlist_candidate_ids=(candidate.candidate_id,),
            selection_kind=SelectionKindV1.PROGRAM,
            selected_candidate_id=candidate.candidate_id,
            selector_identity="owner",
            selected_at=datetime(2026, 8, 23, tzinfo=UTC),
            receipt_identity=ZERO_IDENTITY,
        ),
        result=eligibility,
        snapshot=snapshot,
    )
    binding = VoiceStoryBindingV1(
        story_material_reference="story:1",
        semantic_draft_revision_identity=SHA,
        event_id=1,
        factual_summary_sha256=SHA,
        event_authority_identity=SHA,
    )
    return binding, bundle, eligibility, selection, snapshot, roles, claim


@pytest.mark.parametrize("program_id", [item.program_id for item in PROGRAM_SPECS_V1])
def test_all_reusable_programs_materialize_without_proof_artifacts(program_id):
    binding, bundle, eligibility, selection, snapshot, roles, claim = _context(
        program_id
    )
    ir = materialize_production_ir_v1_1(
        story_binding=binding,
        bundle=bundle,
        eligibility=eligibility,
        mechanic_claim=claim,
        selection=selection,
        repetition_snapshot=snapshot,
        atom_roles=roles,
        activation_policy_identity=ZERO_ACTIVATION_POLICY_V1.policy_identity,
        renderer_identity=RENDERER_IDENTITY,
    )
    rendered = render_production_deterministic_voice_v2(ir)
    request = build_governed_execution_request_v2(
        story_binding=binding,
        fact_atom_bundle=bundle,
        program_eligibility=eligibility,
        mechanic_claim=claim,
        program_selection=selection,
        repetition_snapshot=snapshot,
        activation_policy=ZERO_ACTIVATION_POLICY_V1,
        ir=ir,
    )
    result = DeterministicVoiceExecutorV2(
        activation_policy=ZERO_ACTIVATION_POLICY_V1
    ).execute(request)
    assert ir.authority_kind == "reusable_production_program"
    assert not hasattr(ir, "proof_id")
    assert rendered.commentary_bytes == result.rendered_utf8
    assert rendered.provenance[0].start == 0
    assert rendered.provenance[-1].end == len(rendered.commentary_bytes.decode("utf-8"))
    assert result.model_calls == result.provider_calls == result.model_loads == 0
    assert request == build_governed_execution_request_v2(
        story_binding=binding,
        fact_atom_bundle=bundle,
        program_eligibility=eligibility,
        mechanic_claim=claim,
        program_selection=selection,
        repetition_snapshot=snapshot,
        activation_policy=ZERO_ACTIVATION_POLICY_V1,
        ir=ir,
    )


def test_materializer_fails_closed_for_roles_stale_receipt_and_zero_activation():
    binding, bundle, eligibility, selection, snapshot, roles, claim = _context(
        "NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1"
    )
    wrong = (AtomRoleBindingV1(role="complete_quantity", atom_ids=("p1",)), roles[1])
    wrong_claim = finalize_claim_identity(
        claim.model_copy(update={"atom_roles": wrong, "claim_identity": ZERO_IDENTITY})
    )
    with pytest.raises(ProductionMaterializationError, match="wrong atom role"):
        materialize_production_ir_v1_1(
            story_binding=binding,
            bundle=bundle,
            eligibility=eligibility,
            mechanic_claim=wrong_claim,
            selection=selection,
            repetition_snapshot=snapshot,
            atom_roles=wrong,
            activation_policy_identity=ZERO_ACTIVATION_POLICY_V1.policy_identity,
            renderer_identity=RENDERER_IDENTITY,
        )
    stale = selection.model_copy(update={"eligibility_result_identity": SHA})
    with pytest.raises(ProductionMaterializationError, match="stale selection"):
        materialize_production_ir_v1_1(
            story_binding=binding,
            bundle=bundle,
            eligibility=eligibility,
            mechanic_claim=claim,
            selection=stale,
            repetition_snapshot=snapshot,
            atom_roles=roles,
            activation_policy_identity=ZERO_ACTIVATION_POLICY_V1.policy_identity,
            renderer_identity=RENDERER_IDENTITY,
        )
    with pytest.raises(ProductionMaterializationError, match="activation is zero"):
        materialize_production_ir_v1_1(
            story_binding=binding,
            bundle=bundle,
            eligibility=eligibility,
            mechanic_claim=claim,
            selection=selection,
            repetition_snapshot=snapshot,
            atom_roles=roles,
            activation_policy_identity=ZERO_ACTIVATION_POLICY_V1.policy_identity,
            renderer_identity=RENDERER_IDENTITY,
            expression_selection=SimpleNamespace(
                selection_kind=SimpleNamespace(value="expression")
            ),
        )


def test_retired_and_unknown_surfaces_are_not_production_authority():
    assert PRODUCTION_SURFACE_BY_ID_V1["RF_DAR_STRICT_CA_SCENETA_V1"].retired
    binding, bundle, eligibility, selection, snapshot, roles, claim = _context(
        "FII_BOUNDED_INTAKE_DIALOGUE_V1"
    )
    ir = materialize_production_ir_v1_1(
        story_binding=binding,
        bundle=bundle,
        eligibility=eligibility,
        mechanic_claim=claim,
        selection=selection,
        repetition_snapshot=snapshot,
        atom_roles=roles,
        activation_policy_identity=ZERO_ACTIVATION_POLICY_V1.policy_identity,
        renderer_identity=RENDERER_IDENTITY,
    )
    bad = ir.spans[-1].model_copy(update={"source_identity": "UNKNOWN_SURFACE"})
    with pytest.raises(ValueError, match="unknown production surface"):
        render_production_deterministic_voice_v2(
            ir.model_copy(update={"spans": (*ir.spans[:-1], bad)})
        )


def test_missing_role_and_qualification_mismatch_fail_closed():
    binding, bundle, eligibility, selection, snapshot, roles, claim = _context(
        "USF_ISOLATED_SCENE_AND_EXACT_RETURN_V1"
    )
    missing = roles[:-1]
    missing_claim = finalize_claim_identity(
        claim.model_copy(
            update={"atom_roles": missing, "claim_identity": ZERO_IDENTITY}
        )
    )
    with pytest.raises(ProductionMaterializationError, match="role pattern"):
        materialize_production_ir_v1_1(
            story_binding=binding,
            bundle=bundle,
            eligibility=eligibility,
            mechanic_claim=missing_claim,
            selection=selection,
            repetition_snapshot=snapshot,
            atom_roles=missing,
            activation_policy_identity=ZERO_ACTIVATION_POLICY_V1.policy_identity,
            renderer_identity=RENDERER_IDENTITY,
        )
    changed_atoms = tuple(
        atom.model_copy(update={"qualification_target_atom_ids": ("p2",)})
        if atom.atom_id == "b1"
        else atom
        for atom in bundle.atoms
    )
    changed_bundle = finalize_bundle_identity(
        bundle.model_copy(
            update={"atoms": changed_atoms, "bundle_identity": ZERO_IDENTITY}
        )
    )
    changed_claim = finalize_claim_identity(
        claim.model_copy(
            update={
                "fact_atom_bundle_identity": changed_bundle.bundle_identity,
                "claim_identity": ZERO_IDENTITY,
            }
        )
    )
    changed_eligibility = evaluate_voice_eligibility_v1(
        bundle=changed_bundle,
        claims=(changed_claim,),
        repetition_snapshot=snapshot,
        requested_program_ids=("USF_ISOLATED_SCENE_AND_EXACT_RETURN_V1",),
    )
    changed_candidate = changed_eligibility.shortlist[0]
    changed_selection = finalize_selection_receipt(
        selection.model_copy(
            update={
                "fact_atom_bundle_identity": changed_bundle.bundle_identity,
                "eligibility_result_identity": changed_eligibility.result_identity,
                "shortlist_candidate_ids": (changed_candidate.candidate_id,),
                "selected_candidate_id": changed_candidate.candidate_id,
                "receipt_identity": ZERO_IDENTITY,
            }
        ),
        result=changed_eligibility,
        snapshot=snapshot,
    )
    with pytest.raises(ProductionMaterializationError, match="qualification target"):
        materialize_production_ir_v1_1(
            story_binding=binding,
            bundle=changed_bundle,
            eligibility=changed_eligibility,
            mechanic_claim=changed_claim,
            selection=changed_selection,
            repetition_snapshot=snapshot,
            atom_roles=roles,
            activation_policy_identity=ZERO_ACTIVATION_POLICY_V1.policy_identity,
            renderer_identity=RENDERER_IDENTITY,
        )


def test_executor_rejects_mutated_factual_span_even_with_rehashed_ir():
    binding, bundle, eligibility, selection, snapshot, roles, claim = _context(
        "NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1"
    )
    ir = materialize_production_ir_v1_1(
        story_binding=binding,
        bundle=bundle,
        eligibility=eligibility,
        mechanic_claim=claim,
        selection=selection,
        repetition_snapshot=snapshot,
        atom_roles=roles,
        activation_policy_identity=ZERO_ACTIVATION_POLICY_V1.policy_identity,
        renderer_identity=RENDERER_IDENTITY,
    )
    first = ir.spans[0].model_copy(update={"text": "Fapt inventat."})
    spans = (first, *ir.spans[1:])
    changed = ir.model_copy(
        update={
            "spans": spans,
            "expected_output_sha256": hashlib.sha256(
                "".join(span.text for span in spans).encode("utf-8")
            ).hexdigest(),
        }
    )
    request = build_governed_execution_request_v2(
        story_binding=binding,
        fact_atom_bundle=bundle,
        program_eligibility=eligibility,
        mechanic_claim=claim,
        program_selection=selection,
        repetition_snapshot=snapshot,
        activation_policy=ZERO_ACTIVATION_POLICY_V1,
        ir=changed,
    )
    result = DeterministicVoiceExecutorV2(
        activation_policy=ZERO_ACTIVATION_POLICY_V1
    ).execute(request)
    assert result.kind == "integrity_failure"
    assert result.failure_code == "mutated_factual_ir_span"


def test_explicit_expression_none_receipt_is_bound_without_emitting_a_surface():
    binding, bundle, eligibility, selection, snapshot, roles, claim = _context(
        "FII_CLOSED_OPTION_MENU_V1"
    )
    provisional = ExpressionEligibilityResultV1(
        fact_atom_bundle_identity=bundle.bundle_identity,
        program_eligibility_result_identity=eligibility.result_identity,
        repetition_snapshot_identity=snapshot.snapshot_identity,
        outcomes=(),
        shortlist=(),
    )
    expression_eligibility = provisional.model_copy(
        update={"result_identity": expression_sealed(provisional, "result_identity")}
    )
    expression_selection = finalize_expression_selection_receipt(
        ExpressionOwnerSelectionReceiptV1(
            fact_atom_bundle_identity=bundle.bundle_identity,
            expression_eligibility_result_identity=expression_eligibility.result_identity,
            repetition_snapshot_identity=snapshot.snapshot_identity,
            shortlist_candidate_ids=(),
            selection_kind=ExpressionSelectionKindV1.NONE,
            selector_identity="owner",
            selected_at=datetime(2026, 8, 23, tzinfo=UTC),
        ),
        result=expression_eligibility,
        snapshot=snapshot,
    )
    ir = materialize_production_ir_v1_1(
        story_binding=binding,
        bundle=bundle,
        eligibility=eligibility,
        mechanic_claim=claim,
        selection=selection,
        repetition_snapshot=snapshot,
        atom_roles=roles,
        activation_policy_identity=ZERO_ACTIVATION_POLICY_V1.policy_identity,
        renderer_identity=RENDERER_IDENTITY,
        expression_selection=expression_selection,
    )
    request = build_governed_execution_request_v2(
        story_binding=binding,
        fact_atom_bundle=bundle,
        program_eligibility=eligibility,
        mechanic_claim=claim,
        program_selection=selection,
        expression_eligibility=expression_eligibility,
        expression_selection=expression_selection,
        repetition_snapshot=snapshot,
        activation_policy=ZERO_ACTIVATION_POLICY_V1,
        ir=ir,
    )
    result = DeterministicVoiceExecutorV2(
        activation_policy=ZERO_ACTIVATION_POLICY_V1
    ).execute(request)
    assert (
        ir.expression_selection_receipt_identity
        == expression_selection.receipt_identity
    )
    assert result.kind == "generated"
