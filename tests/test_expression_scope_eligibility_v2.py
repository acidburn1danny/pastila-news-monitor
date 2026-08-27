from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.expression_catalog_v2 import (
    ALL_SCOPE_SPECS_V1,
    BOUNDED_POOL_SCOPE_SPECS_V1,
    EVIDENCE_ONLY_EXPRESSION_ID,
    FIRST_TWELVE_SCOPE_SPECS_V1,
    SCOPE_SPECS_V1,
    CommentaryRelationBindingV1,
    ExpressionEligibilityIntegrityError,
    ExpressionEligibilityStatusV1,
    ExpressionOwnerSelectionReceiptV1,
    ExpressionSelectionKindV1,
    ExpressionSelectionReceiptStoreV1,
    IntegratedExpressionProofArtifactV1,
    IntegratedExpressionProofStoreV1,
    RelationAtomRoleV1,
    UnknownExpressionSelectionReceiptVersionError,
    evaluate_expression_eligibility_v1,
    expression_repetition_identity,
    finalize_expression_selection_receipt,
    finalize_integrated_expression_artifact_v1,
    finalize_relation_binding_identity,
    integrate_expression_selection_v1,
    load_expression_catalog_overlay_v2,
    render_integrated_expression_v1,
)
from pastila_scout.expression_catalog_v2.models import RenderabilityStatusV2
from pastila_scout.expression_retrieval_v1.catalog import load_catalog_v1
from pastila_scout.voice_deterministic_v2 import (
    DeterministicVoiceValidationError,
    MechanicIdV1,
    ProvenanceClassV1,
    build_frozen_realization_ir,
)
from pastila_scout.voice_eligibility_v2 import (
    ZERO_IDENTITY,
    AtomRoleBindingV1,
    MechanicEligibilityClaimV1,
    RepetitionUseV1,
    VoiceRepetitionSnapshotV1,
    evaluate_voice_eligibility_v1,
    finalize_claim_identity,
    finalize_repetition_snapshot,
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

SHA = "sha256:" + "1" * 64
FROZEN_PROOF_CASES = Path("tests/fixtures/voice_deterministic_v2/frozen_proof_cases")
EXPECTED_SURFACES = {
    "ro-expression-v1:2e5417acdb78ee504d4b": "A aduce apă după ce s-a stins focul",
    "ro-expression-v1:746823d11b1460dac265": "Aici vorbim de bătut apa-n piuă.",
    "ro-expression-v1:41136a4e8443b1239535": (
        "Aici e fix cu vândutul castraveților grădinarului."
    ),
    "ro-expression-v1:b37979ce96f5d03deda3": (
        "Și uite așa ajungem la clasica coadă de pește."
    ),
    "ro-expression-v1:2aaa6fa3011f6a2ea8f0": (
        "Aici deja vorbim de pus batista pe țambal."
    ),
    "ro-expression-v1:2b65e40f861c797989a7": (
        "Și uite așa ajungem la clasica întoarcere ca la Ploiești."
    ),
    "ro-expression-v1:8c165e82d1f7002717ed": ("Calul de dar nu se caută la dinți"),
}
EXPECTED_SURFACES.update(
    {
        "ro-expression-v1:291dc70a3335d6c5a326": "Și uite așa apare clasica apă la moară.",
        "ro-expression-v1:499847b2e206c615cb3f": "Și aici avem clasica situație: prins cu mâța-n sac.",
        "ro-expression-v1:5d8d914aa7485bd00357": "Aici vorbim de o garanție la nivel de „mâna în foc”.",
        "ro-expression-v1:741a112a615fd83b70c7": "Pe românește: „și-a pus cenușă-n cap”.",
        "ro-expression-v1:7ad0710287d639d1402e": "Pisica blândă zgârie rău",
        "ro-expression-v1:844dedd262d2b832d6ee": "Asta deja seamănă cu un cec în alb.",
        "ro-expression-v1:9061edfa9121f3caa7c6": "La atâta analiză, nu mai rămâne fir de despicat.",
        "ro-expression-v1:a128853989c1ea8dbc10": "Și uite așa se calcă pe bec.",
        "ro-expression-v1:a932575dfe8f1ed9134b": "La pomul lăudat să nu te duci cu sacul",
        "ro-expression-v1:cb128a3e07f2dbd87808": "Și uite așa apare cioara vopsită.",
        "ro-expression-v1:ee71f9fb9de0fe424b4c": "Și uite așa se iese basma curată.",
        "ro-expression-v1:fd75f40659d177a3a038": "Aici facem haz de necaz.",
    }
)
EXPECTED_SURFACES.update(
    {
        "ro-expression-v1:1068794b4bf34c8914dc": "Și uite așa o dai de oaie.",
        "ro-expression-v1:65f9b0c32e8e886b8d0f": "Și uite așa ajunge oiștea-n gard.",
        "ro-expression-v1:0e6562965022d3dd391f": "Aici deja sare muștarul.",
        "ro-expression-v1:2ae8cdb574c10fbc2328": "Scos din pepeni. Complet.",
        "ro-expression-v1:3df48761977436d385be": (
            "Asta e deja luptă cu morile de vânt."
        ),
        "ro-expression-v1:e9c624855a4d33760669": ("Pielea ursului? Deja la vânzare."),
        "ro-expression-v1:7a7cb37228c5608408c6": ("Și gata. Cuțitul a ajuns la os."),
        "ro-expression-v1:34d94191a3c600bc4f26": ("Și s-a dus pe Apa Sâmbetei."),
    }
)


def _candidate(candidate_id: str, text: str, kind=CandidateKind.EXACT_SPAN):
    evidence = AuthorityPassageV1(
        authority_class=AuthorityClass.EVENT,
        authority_identity=SHA,
        source_identity="independent-proof-authority",
        passage=text,
        start=0,
        end=len(text),
    )
    return SurfaceCandidateV1(
        candidate_id=candidate_id,
        kind=kind,
        evidence=evidence,
        normalized_key=text.casefold(),
        extraction_receipt_identity=SHA,
    )


def _proof_bundle():
    candidate_specs = [
        ("program-event", "Un fapt acceptat.", AtomKind.EVENT_PROPOSITION)
    ]
    candidate_specs.append(("program-quantity", "10 lei", AtomKind.COMPLETE_QUANTITY))
    for spec in ALL_SCOPE_SPECS_V1:
        for role in spec.required_roles:
            candidate_specs.append(
                (
                    f"{spec.expression_id}:{role}",
                    f"Fapt acceptat pentru {role}.",
                    AtomKind.EVENT_PROPOSITION,
                )
            )
    candidates = tuple(
        _candidate(identity, text) for identity, text, _ in candidate_specs
    )
    atoms = []
    for (identity, text, kind), candidate in zip(
        candidate_specs, candidates, strict=True
    ):
        quantity = None
        if kind is AtomKind.COMPLETE_QUANTITY:
            quantity = CompleteQuantityV1(
                exact_surface=text,
                numeric_surface="10",
                bound_semantics="exact",
                unit_or_currency="lei",
                subject_scope="proof",
            )
        atoms.append(
            FactAtomV1(
                atom_id=identity,
                kind=kind,
                proposition=text,
                authority_class=AuthorityClass.EVENT,
                evidence=(candidate.evidence,),
                candidate_ids=(candidate.candidate_id,),
                quantity=quantity,
            )
        )
    return finalize_bundle_identity(
        VoiceFactAtomBundleV1(
            revision=1,
            semantic_draft_revision_identity=SHA,
            event_id=9001,
            story_position=1,
            factual_summary_identity=SHA,
            event_authority_identity=SHA,
            candidates=candidates,
            atoms=tuple(atoms),
            adjudication_receipt_identities=(SHA,),
            bundle_identity=ZERO_IDENTITY,
        )
    )


def _snapshot(*uses, episode=10, position=3):
    return finalize_repetition_snapshot(
        VoiceRepetitionSnapshotV1(
            current_episode_ordinal=episode,
            current_story_position=position,
            uses=uses,
            snapshot_identity=ZERO_IDENTITY,
        )
    )


def _program(bundle, snapshot):
    claim = finalize_claim_identity(
        MechanicEligibilityClaimV1(
            fact_atom_bundle_identity=bundle.bundle_identity,
            mechanic_id=MechanicIdV1.NUMERIC_EXPECTATION_LADDER,
            atom_roles=(
                AtomRoleBindingV1(
                    role="governed_atoms",
                    atom_ids=("program-event", "program-quantity"),
                ),
            ),
            satisfied_boundary_codes=tuple(
                sorted(
                    {
                        "no_value_judgment",
                        "preserve_approximation_attribution_period_denominator_scope",
                    }
                )
            ),
            adjudication_receipt_identity=SHA,
            claim_identity=ZERO_IDENTITY,
        )
    )
    result = evaluate_voice_eligibility_v1(
        bundle=bundle,
        claims=(claim,),
        repetition_snapshot=snapshot,
        requested_program_ids=("NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1",),
    )
    return result, result.shortlist[0]


def _binding(spec, bundle, program_id, *, constraints=None, roles=None):
    role_names = roles if roles is not None else spec.required_roles
    provisional = CommentaryRelationBindingV1(
        fact_atom_bundle_identity=bundle.bundle_identity,
        relationship=spec.relationship,
        atom_roles=tuple(
            RelationAtomRoleV1(
                role=role,
                atom_ids=(f"{spec.expression_id}:{role}",),
            )
            for role in role_names
        ),
        satisfied_constraint_codes=(
            spec.required_constraint_codes if constraints is None else constraints
        ),
        compatible_program_ids=(program_id,),
        adjudication_receipt_identity=SHA,
        owner_or_editor_identity="independent-proof-adjudicator",
        binding_identity=ZERO_IDENTITY,
    )
    return finalize_relation_binding_identity(provisional)


def _evaluate(bindings=(), snapshot=None, overlay=None):
    bundle = _proof_bundle()
    snapshot = snapshot or _snapshot()
    program_result, program = _program(bundle, snapshot)
    resolved = tuple(
        _binding(spec, bundle, program.program_id) if spec in bindings else spec
        for spec in bindings
    )
    return (
        bundle,
        snapshot,
        program_result,
        program,
        evaluate_expression_eligibility_v1(
            bundle=bundle,
            bindings=resolved,
            program_result=program_result,
            selected_program_candidate=program,
            repetition_snapshot=snapshot,
            overlay=overlay or load_expression_catalog_overlay_v2(),
            catalog=load_catalog_v1(use_cache=False),
        ),
    )


@pytest.mark.parametrize(
    "spec", SCOPE_SPECS_V1, ids=lambda item: item.relationship.value
)
def test_each_approved_scope_has_an_independent_positive_and_exact_surface(spec):
    _, _, _, _, result = _evaluate((spec,))
    assert [item.expression_id for item in result.shortlist] == [spec.expression_id]
    candidate = result.shortlist[0]
    assert candidate.exact_surface == EXPECTED_SURFACES[spec.expression_id]
    assert candidate.surface_utf8_sha256
    assert result.model_calls == result.provider_calls == 0


def test_multiple_bindings_produce_sorted_shortlist_without_selection():
    _, _, _, _, result = _evaluate(SCOPE_SPECS_V1)
    assert len(result.shortlist) == 7
    assert [item.expression_id for item in result.shortlist] == sorted(
        item.expression_id for item in result.shortlist
    )
    assert not result.production_active


def test_missing_binding_category_similarity_and_evidence_only_all_abstain():
    _, _, _, _, result = _evaluate()
    assert not result.shortlist
    outcomes = {item.expression_id: item for item in result.outcomes}
    assert all(
        "missing_explicit_relation_binding" in outcomes[spec.expression_id].reason_codes
        for spec in SCOPE_SPECS_V1
    )
    assert outcomes[EVIDENCE_ONLY_EXPRESSION_ID].reason_codes == (
        "evidence_only_never_eligible",
    )


@pytest.mark.parametrize(
    ("spec", "missing_constraint"),
    tuple(
        (spec, constraint)
        for spec in SCOPE_SPECS_V1
        for constraint in spec.required_constraint_codes
    ),
    ids=lambda value: (
        value.relationship.value if hasattr(value, "relationship") else str(value)
    ),
)
def test_every_frozen_distinction_fails_closed_when_missing(spec, missing_constraint):
    bundle = _proof_bundle()
    snapshot = _snapshot()
    program_result, program = _program(bundle, snapshot)
    binding = _binding(
        spec,
        bundle,
        program.program_id,
        constraints=tuple(
            item
            for item in spec.required_constraint_codes
            if item != missing_constraint
        ),
    )
    result = evaluate_expression_eligibility_v1(
        bundle=bundle,
        bindings=(binding,),
        program_result=program_result,
        selected_program_candidate=program,
        repetition_snapshot=snapshot,
        overlay=load_expression_catalog_overlay_v2(),
        catalog=load_catalog_v1(use_cache=False),
    )
    outcome = next(
        item for item in result.outcomes if item.expression_id == spec.expression_id
    )
    assert outcome.status is ExpressionEligibilityStatusV1.INELIGIBLE
    assert "frozen_relationship_constraints_unsatisfied" in outcome.reason_codes


def test_actor_chronology_and_program_compatibility_fail_closed():
    spec = next(
        item
        for item in SCOPE_SPECS_V1
        if item.relationship.value == "SUPPORTED_POSITION_OR_VERSION_REVERSAL"
    )
    bundle = _proof_bundle()
    snapshot = _snapshot()
    program_result, program = _program(bundle, snapshot)
    wrong_roles = tuple(role for role in spec.required_roles if role != "actor")
    actor_mismatch = _binding(spec, bundle, program.program_id, roles=wrong_roles)
    wrong_program = _binding(spec, bundle, "ANOTHER_PROGRAM")
    for binding, reason in (
        (actor_mismatch, "required_atom_roles_mismatch"),
        (wrong_program, "selected_program_incompatible"),
    ):
        result = evaluate_expression_eligibility_v1(
            bundle=bundle,
            bindings=(binding,),
            program_result=program_result,
            selected_program_candidate=program,
            repetition_snapshot=snapshot,
            overlay=load_expression_catalog_overlay_v2(),
            catalog=load_catalog_v1(use_cache=False),
        )
        outcome = next(
            item for item in result.outcomes if item.expression_id == spec.expression_id
        )
        assert reason in outcome.reason_codes


def test_stale_and_unknown_atom_bindings_raise_integrity_errors():
    spec = SCOPE_SPECS_V1[0]
    bundle = _proof_bundle()
    snapshot = _snapshot()
    program_result, program = _program(bundle, snapshot)
    valid = _binding(spec, bundle, program.program_id)
    stale = finalize_relation_binding_identity(
        valid.model_copy(
            update={"fact_atom_bundle_identity": SHA, "binding_identity": ZERO_IDENTITY}
        )
    )
    role = valid.atom_roles[0].model_copy(update={"atom_ids": ("unknown-atom",)})
    unknown = finalize_relation_binding_identity(
        valid.model_copy(
            update={
                "atom_roles": (role,) + valid.atom_roles[1:],
                "binding_identity": ZERO_IDENTITY,
            }
        )
    )
    for binding, message in ((stale, "stale"), (unknown, "unknown atom")):
        with pytest.raises(ExpressionEligibilityIntegrityError, match=message):
            evaluate_expression_eligibility_v1(
                bundle=bundle,
                bindings=(binding,),
                program_result=program_result,
                selected_program_candidate=program,
                repetition_snapshot=snapshot,
                overlay=load_expression_catalog_overlay_v2(),
                catalog=load_catalog_v1(use_cache=False),
            )


def test_background_authority_cannot_establish_event_relationship():
    spec = SCOPE_SPECS_V1[0]
    bundle = _proof_bundle()
    target_id = f"{spec.expression_id}:{spec.required_roles[0]}"
    atoms = tuple(
        atom.model_copy(
            update={
                "authority_class": AuthorityClass.BACKGROUND,
                "prohibits_event_projection": True,
                "evidence": tuple(
                    item.model_copy(
                        update={"authority_class": AuthorityClass.BACKGROUND}
                    )
                    for item in atom.evidence
                ),
            }
        )
        if atom.atom_id == target_id
        else atom
        for atom in bundle.atoms
    )
    bundle = finalize_bundle_identity(
        bundle.model_copy(
            update={
                "atoms": atoms,
                "background_authority_identity": SHA,
                "bundle_identity": ZERO_IDENTITY,
            }
        )
    )
    snapshot = _snapshot()
    program_result, program = _program(bundle, snapshot)
    binding = _binding(spec, bundle, program.program_id)
    result = evaluate_expression_eligibility_v1(
        bundle=bundle,
        bindings=(binding,),
        program_result=program_result,
        selected_program_candidate=program,
        repetition_snapshot=snapshot,
        overlay=load_expression_catalog_overlay_v2(),
        catalog=load_catalog_v1(use_cache=False),
    )
    outcome = next(
        item for item in result.outcomes if item.expression_id == spec.expression_id
    )
    assert "event_relationship_requires_event_authority" in outcome.reason_codes


def test_unrenderable_approved_record_is_ineligible_without_surface_repair():
    spec = SCOPE_SPECS_V1[1]
    overlay = load_expression_catalog_overlay_v2()
    records = tuple(
        item.model_copy(
            update={
                "renderability_status": RenderabilityStatusV2.UNAVAILABLE,
                "approved_surface_ids": (),
            }
        )
        if item.expression_id == spec.expression_id
        else item
        for item in overlay.records
    )
    altered = overlay.model_copy(update={"records": records})
    _, _, _, _, result = _evaluate((spec,), overlay=altered)
    outcome = next(
        item for item in result.outcomes if item.expression_id == spec.expression_id
    )
    assert "approved_exact_surface_unavailable" in outcome.reason_codes


def test_repetition_episode_adjacency_and_cooldown_exhaust_to_omission():
    spec = SCOPE_SPECS_V1[1]
    bundle = _proof_bundle()
    empty = _snapshot()
    program_result, program = _program(bundle, empty)
    identity = expression_repetition_identity(
        spec.expression_id, spec.family_identity, spec.relationship
    )
    surface_id = "SURFACE_BATE_APA_N_PIUA_STANDALONE_CONCLUSION_V1"
    uses = (
        RepetitionUseV1(
            episode_ordinal=10,
            story_position=1,
            mechanic_id=MechanicIdV1.FICTIONAL_INTAKE_OR_INTERFACE,
            program_id="FII_BOUNDED_INTAKE_DIALOGUE_V1",
            cadence_signature="prior-cadence",
            surface_ids=(surface_id,),
            enrichment_identity=identity,
        ),
    )
    for snapshot in (
        _snapshot(*uses),
        _snapshot(uses[0].model_copy(update={"story_position": 2})),
        _snapshot(uses[0].model_copy(update={"episode_ordinal": 7})),
    ):
        program_result, program = _program(bundle, snapshot)
        binding = _binding(spec, bundle, program.program_id)
        result = evaluate_expression_eligibility_v1(
            bundle=bundle,
            bindings=(binding,),
            program_result=program_result,
            selected_program_candidate=program,
            repetition_snapshot=snapshot,
            overlay=load_expression_catalog_overlay_v2(),
            catalog=load_catalog_v1(use_cache=False),
        )
        assert not result.shortlist


def test_explicit_selection_and_none_receipts_are_deterministic_and_persist(tmp_path):
    bundle, snapshot, _, _, result = _evaluate((SCOPE_SPECS_V1[0],))
    common = {
        "fact_atom_bundle_identity": bundle.bundle_identity,
        "expression_eligibility_result_identity": result.result_identity,
        "repetition_snapshot_identity": snapshot.snapshot_identity,
        "shortlist_candidate_ids": tuple(
            item.candidate_id for item in result.shortlist
        ),
        "selector_identity": "owner",
        "selected_at": datetime(2026, 8, 22, tzinfo=UTC),
        "receipt_identity": ZERO_IDENTITY,
    }
    selected = finalize_expression_selection_receipt(
        ExpressionOwnerSelectionReceiptV1(
            **common,
            selection_kind=ExpressionSelectionKindV1.EXPRESSION,
            selected_candidate_id=result.shortlist[0].candidate_id,
        ),
        result=result,
        snapshot=snapshot,
    )
    omitted = finalize_expression_selection_receipt(
        ExpressionOwnerSelectionReceiptV1(
            **common, selection_kind=ExpressionSelectionKindV1.NONE
        ),
        result=result,
        snapshot=snapshot,
    )
    assert selected.selected_candidate_id
    assert omitted.selected_candidate_id is None
    store = ExpressionSelectionReceiptStoreV1(tmp_path / "receipt.json")
    store.save(omitted)
    assert store.load() == omitted
    store.save(omitted)
    assert store.load().receipt_identity == omitted.receipt_identity

    value = json.loads((tmp_path / "receipt.json").read_text(encoding="utf-8"))
    value["schema_version"] = "2"
    (tmp_path / "receipt.json").write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(UnknownExpressionSelectionReceiptVersionError):
        store.load()


@pytest.mark.parametrize(
    "spec", FIRST_TWELVE_SCOPE_SPECS_V1, ids=lambda item: item.relationship.value
)
def test_each_first_twelve_scope_has_positive_eligibility_and_exact_surface(spec):
    _, _, _, _, result = _evaluate((spec,))
    assert [item.expression_id for item in result.shortlist] == [spec.expression_id]
    candidate = result.shortlist[0]
    assert candidate.exact_surface == EXPECTED_SURFACES[spec.expression_id]
    assert (
        candidate.surface_utf8_sha256
        == hashlib.sha256(candidate.exact_surface.encode("utf-8")).hexdigest()
    )
    assert result.model_calls == result.provider_calls == 0


@pytest.mark.parametrize(
    ("spec", "missing_constraint"),
    tuple(
        (spec, constraint)
        for spec in FIRST_TWELVE_SCOPE_SPECS_V1
        for constraint in spec.required_constraint_codes
    ),
)
def test_first_twelve_near_fit_distinctions_fail_closed(spec, missing_constraint):
    bundle = _proof_bundle()
    snapshot = _snapshot()
    program_result, program = _program(bundle, snapshot)
    binding = _binding(
        spec,
        bundle,
        program.program_id,
        constraints=tuple(
            code
            for code in spec.required_constraint_codes
            if code != missing_constraint
        ),
    )
    result = evaluate_expression_eligibility_v1(
        bundle=bundle,
        bindings=(binding,),
        program_result=program_result,
        selected_program_candidate=program,
        repetition_snapshot=snapshot,
        overlay=load_expression_catalog_overlay_v2(),
        catalog=load_catalog_v1(use_cache=False),
    )
    outcome = next(
        item for item in result.outcomes if item.expression_id == spec.expression_id
    )
    assert outcome.status is ExpressionEligibilityStatusV1.INELIGIBLE
    assert "frozen_relationship_constraints_unsatisfied" in outcome.reason_codes


def test_first_twelve_multiple_eligible_are_sorted_without_automatic_winner():
    _, _, _, _, result = _evaluate(FIRST_TWELVE_SCOPE_SPECS_V1)
    assert len(result.shortlist) == 12
    assert [item.expression_id for item in result.shortlist] == sorted(
        item.expression_id for item in result.shortlist
    )
    assert not result.production_active


def test_haz_de_necaz_collision_has_one_canonical_candidate_only():
    spec = next(
        item
        for item in FIRST_TWELVE_SCOPE_SPECS_V1
        if item.expression_id == "ro-expression-v1:fd75f40659d177a3a038"
    )
    _, _, _, _, result = _evaluate((spec,))
    assert len(result.shortlist) == 1
    assert (
        result.shortlist[0].surface_id == "SURFACE_HAZ_DE_NECAZ_EDITORIAL_RESPONSE_V1"
    )
    overlay = load_expression_catalog_overlay_v2()
    legacy = next(
        item
        for item in overlay.preferred_surface_evidence
        if item.surface_id == "surface-v1:07"
    )
    assert not legacy.voice_v2_authorized
    assert all(item.surface_id != "surface-v1:07" for item in result.shortlist)


def test_unreviewed_expression_remains_unavailable_and_cannot_shortlist():
    overlay = load_expression_catalog_overlay_v2()
    unreviewed_id = overlay.owner_review_queue[0].expression_id
    _, _, _, _, result = _evaluate()
    assert unreviewed_id not in {item.expression_id for item in result.shortlist}
    assert unreviewed_id not in {item.expression_id for item in result.outcomes}


def test_first_twelve_role_order_is_semantic_and_fails_closed_when_reversed():
    spec = FIRST_TWELVE_SCOPE_SPECS_V1[0]
    bundle = _proof_bundle()
    snapshot = _snapshot()
    program_result, program = _program(bundle, snapshot)
    binding = _binding(
        spec, bundle, program.program_id, roles=tuple(reversed(spec.required_roles))
    )
    result = evaluate_expression_eligibility_v1(
        bundle=bundle,
        bindings=(binding,),
        program_result=program_result,
        selected_program_candidate=program,
        repetition_snapshot=snapshot,
        overlay=load_expression_catalog_overlay_v2(),
        catalog=load_catalog_v1(use_cache=False),
    )
    outcome = next(
        item for item in result.outcomes if item.expression_id == spec.expression_id
    )
    assert "required_atom_roles_mismatch" in outcome.reason_codes


def test_declared_background_role_is_allowed_but_event_roles_remain_event_bound():
    spec = FIRST_TWELVE_SCOPE_SPECS_V1[0]
    allowed_id = f"{spec.expression_id}:existing_recipient_position_or_process"
    bundle = _proof_bundle()
    atoms = tuple(
        atom.model_copy(
            update={
                "authority_class": AuthorityClass.BACKGROUND,
                "prohibits_event_projection": True,
                "evidence": tuple(
                    evidence.model_copy(
                        update={"authority_class": AuthorityClass.BACKGROUND}
                    )
                    for evidence in atom.evidence
                ),
            }
        )
        if atom.atom_id == allowed_id
        else atom
        for atom in bundle.atoms
    )
    bundle = finalize_bundle_identity(
        bundle.model_copy(
            update={
                "atoms": atoms,
                "background_authority_identity": SHA,
                "bundle_identity": ZERO_IDENTITY,
            }
        )
    )
    snapshot = _snapshot()
    program_result, program = _program(bundle, snapshot)
    binding = _binding(spec, bundle, program.program_id)
    result = evaluate_expression_eligibility_v1(
        bundle=bundle,
        bindings=(binding,),
        program_result=program_result,
        selected_program_candidate=program,
        repetition_snapshot=snapshot,
        overlay=load_expression_catalog_overlay_v2(),
        catalog=load_catalog_v1(use_cache=False),
    )
    assert [item.expression_id for item in result.shortlist] == [spec.expression_id]


def test_first_twelve_family_identity_exhaustion_blocks_sibling_identity():
    spec = FIRST_TWELVE_SCOPE_SPECS_V1[0]
    bundle = _proof_bundle()
    prior_family_use = RepetitionUseV1(
        episode_ordinal=10,
        story_position=1,
        mechanic_id=MechanicIdV1.FICTIONAL_INTAKE_OR_INTERFACE,
        program_id="FII_BOUNDED_INTAKE_DIALOGUE_V1",
        cadence_signature="prior-family-cadence",
        enrichment_identity=(
            f"expression-v2|different-expression|{spec.family_identity}|"
            f"{spec.relationship.value}"
        ),
    )
    snapshot = _snapshot(prior_family_use)
    program_result, program = _program(bundle, snapshot)
    binding = _binding(spec, bundle, program.program_id)
    result = evaluate_expression_eligibility_v1(
        bundle=bundle,
        bindings=(binding,),
        program_result=program_result,
        selected_program_candidate=program,
        repetition_snapshot=snapshot,
        overlay=load_expression_catalog_overlay_v2(),
        catalog=load_catalog_v1(use_cache=False),
    )
    outcome = next(
        item for item in result.outcomes if item.expression_id == spec.expression_id
    )
    assert "expression_family_episode_ceiling" in outcome.reason_codes
    assert not result.shortlist


def test_first_twelve_surface_contract_mismatch_fails_closed():
    spec = next(
        item
        for item in FIRST_TWELVE_SCOPE_SPECS_V1
        if item.expression_id == "ro-expression-v1:291dc70a3335d6c5a326"
    )
    bundle = _proof_bundle()
    snapshot = _snapshot()
    program_result, program = _program(bundle, snapshot)
    binding = _binding(spec, bundle, program.program_id)
    overlay = load_expression_catalog_overlay_v2()
    surfaces = tuple(
        surface.model_copy(update={"expression_family_identity": "wrong-family"})
        if surface.expression_id == spec.expression_id
        else surface
        for surface in overlay.approved_surfaces
    )
    overlay = overlay.model_copy(update={"approved_surfaces": surfaces})

    result = evaluate_expression_eligibility_v1(
        bundle=bundle,
        bindings=(binding,),
        program_result=program_result,
        selected_program_candidate=program,
        repetition_snapshot=snapshot,
        overlay=overlay,
        catalog=load_catalog_v1(use_cache=False),
    )

    outcome = next(
        item for item in result.outcomes if item.expression_id == spec.expression_id
    )
    assert "approved_exact_surface_unavailable" in outcome.reason_codes
    assert not result.shortlist


def _selection_receipt(bundle, snapshot, result, candidate_id=None):
    receipt = ExpressionOwnerSelectionReceiptV1(
        fact_atom_bundle_identity=bundle.bundle_identity,
        expression_eligibility_result_identity=result.result_identity,
        repetition_snapshot_identity=snapshot.snapshot_identity,
        shortlist_candidate_ids=tuple(item.candidate_id for item in result.shortlist),
        selection_kind=(
            ExpressionSelectionKindV1.EXPRESSION
            if candidate_id
            else ExpressionSelectionKindV1.NONE
        ),
        selected_candidate_id=candidate_id,
        selector_identity="integrated-proof-owner",
        selected_at=datetime(2026, 8, 23, tzinfo=UTC),
        receipt_identity=ZERO_IDENTITY,
    )
    return finalize_expression_selection_receipt(
        receipt, result=result, snapshot=snapshot
    )


def _pool_evaluation(specs, snapshot=None):
    bundle = _proof_bundle()
    snapshot = snapshot or _snapshot(position=4)
    program_result, program = _program(bundle, snapshot)
    bindings = tuple(_binding(spec, bundle, program.program_id) for spec in specs)
    result = evaluate_expression_eligibility_v1(
        bundle=bundle,
        bindings=bindings,
        program_result=program_result,
        selected_program_candidate=program,
        repetition_snapshot=snapshot,
        overlay=load_expression_catalog_overlay_v2(),
        catalog=load_catalog_v1(use_cache=False),
    )
    return bundle, snapshot, bindings, result


def test_symmetric_pool_supports_both_owner_choices_none_and_exact_fallback(tmp_path):
    specs = BOUNDED_POOL_SCOPE_SPECS_V1[:2]
    bundle, snapshot, bindings, result = _pool_evaluation(specs)
    assert [item.expression_id for item in result.shortlist] == sorted(
        item.expression_id for item in specs
    )
    assert {item.pool_identity for item in result.shortlist} == {
        "EXPRESSION_POOL_OBVIOUS_BLUNDER_OR_FAILED_EXECUTION_V1"
    }
    base_ir = build_frozen_realization_ir("P1", FROZEN_PROOF_CASES)
    rendered = []
    for candidate in result.shortlist:
        receipt = _selection_receipt(bundle, snapshot, result, candidate.candidate_id)
        ir = integrate_expression_selection_v1(
            base_ir=base_ir,
            eligibility_result=result,
            selection_receipt=receipt,
            relation_bindings=bindings,
            repetition_snapshot=snapshot,
        )
        output = render_integrated_expression_v1(
            ir=ir,
            eligibility_result=result,
            selection_receipt=receipt,
            relation_bindings=bindings,
            repetition_snapshot=snapshot,
        )
        assert output.commentary_bytes.endswith(candidate.exact_surface.encode())
        assert output.provenance[-1].provenance_class is (
            ProvenanceClassV1.APPROVED_EXPRESSION_SURFACE
        )
        assert output.provenance[-1].expression_binding.pool_identity == (
            candidate.pool_identity
        )
        assert output.model_calls == output.provider_calls == 0
        rendered.append(output.commentary_bytes)
    assert rendered[0] != rendered[1]

    none_receipt = _selection_receipt(bundle, snapshot, result)
    none_ir = integrate_expression_selection_v1(
        base_ir=base_ir,
        eligibility_result=result,
        selection_receipt=none_receipt,
        relation_bindings=bindings,
        repetition_snapshot=snapshot,
    )
    assert none_ir == base_ir
    none_output = render_integrated_expression_v1(
        ir=none_ir,
        eligibility_result=result,
        selection_receipt=none_receipt,
        relation_bindings=bindings,
        repetition_snapshot=snapshot,
    )
    assert not any(
        span.provenance_class is ProvenanceClassV1.APPROVED_EXPRESSION_SURFACE
        for span in none_output.provenance
    )
    assert all(
        candidate.exact_surface.encode() not in none_output.commentary_bytes
        for candidate in result.shortlist
    )

    selected = result.shortlist[0]
    exact_use = RepetitionUseV1(
        episode_ordinal=10,
        story_position=1,
        mechanic_id=MechanicIdV1.FICTIONAL_INTAKE_OR_INTERFACE,
        program_id="prior-program",
        cadence_signature="prior-exact-surface",
        surface_ids=(selected.surface_id,),
    )
    _, _, _, fallback = _pool_evaluation(specs, _snapshot(exact_use, position=4))
    assert [item.expression_id for item in fallback.shortlist] == [
        item.expression_id for item in result.shortlist if item != selected
    ]


def test_shared_pool_family_use_exhausts_both_without_unrelated_fallback():
    specs = BOUNDED_POOL_SCOPE_SPECS_V1[:2]
    _, _, _, initial = _pool_evaluation(specs)
    selected = initial.shortlist[0]
    family_use = RepetitionUseV1(
        episode_ordinal=10,
        story_position=1,
        mechanic_id=MechanicIdV1.FICTIONAL_INTAKE_OR_INTERFACE,
        program_id="prior-program",
        cadence_signature="prior-family-use",
        surface_ids=(selected.surface_id,),
        enrichment_identity=selected.repetition_identity,
    )
    _, _, _, exhausted = _pool_evaluation(specs, _snapshot(family_use, position=4))
    assert not exhausted.shortlist
    assert all(
        "expression_family_episode_ceiling" in item.reason_codes
        for item in exhausted.outcomes
        if item.expression_id in {spec.expression_id for spec in specs}
    )


def test_asymmetric_anger_pool_preserves_stricter_trigger_binding():
    broad, strict = BOUNDED_POOL_SCOPE_SPECS_V1[2:4]
    _, _, _, broad_only = _pool_evaluation((broad,))
    assert [item.expression_id for item in broad_only.shortlist] == [
        broad.expression_id
    ]
    strict_outcome = next(
        item
        for item in broad_only.outcomes
        if item.expression_id == strict.expression_id
    )
    assert "required_atom_roles_mismatch" in strict_outcome.reason_codes

    _, _, _, both = _pool_evaluation((broad, strict))
    assert {item.expression_id for item in both.shortlist} == {
        broad.expression_id,
        strict.expression_id,
    }


def test_integrated_expression_integrity_rejects_pool_surface_and_receipt_drift():
    specs = BOUNDED_POOL_SCOPE_SPECS_V1[:2]
    bundle, snapshot, bindings, result = _pool_evaluation(specs)
    receipt = _selection_receipt(
        bundle, snapshot, result, result.shortlist[0].candidate_id
    )
    base_ir = build_frozen_realization_ir("P1", FROZEN_PROOF_CASES)
    ir = integrate_expression_selection_v1(
        base_ir=base_ir,
        eligibility_result=result,
        selection_receipt=receipt,
        relation_bindings=bindings,
        repetition_snapshot=snapshot,
    )
    expression_span = ir.spans[-1]
    wrong_binding = expression_span.expression_binding.model_copy(
        update={"pool_identity": "WRONG_POOL"}
    )
    mutated = ir.model_copy(
        update={
            "spans": ir.spans[:-1]
            + (
                expression_span.model_copy(
                    update={"expression_binding": wrong_binding}
                ),
            )
        }
    )
    with pytest.raises(
        DeterministicVoiceValidationError,
        match="does not match governed selection",
    ):
        render_integrated_expression_v1(
            ir=mutated,
            eligibility_result=result,
            selection_receipt=receipt,
            relation_bindings=bindings,
            repetition_snapshot=snapshot,
        )

    stale = receipt.model_copy(
        update={"expression_eligibility_result_identity": ZERO_IDENTITY}
    )
    with pytest.raises(ExpressionEligibilityIntegrityError):
        render_integrated_expression_v1(
            ir=ir,
            eligibility_result=result,
            selection_receipt=stale,
            relation_bindings=bindings,
            repetition_snapshot=snapshot,
        )

    stale_binding = bindings[0].model_copy(
        update={"owner_or_editor_identity": "tampered-owner"}
    )
    with pytest.raises(ExpressionEligibilityIntegrityError):
        render_integrated_expression_v1(
            ir=ir,
            eligibility_result=result,
            selection_receipt=receipt,
            relation_bindings=(stale_binding,) + bindings[1:],
            repetition_snapshot=snapshot,
        )


def test_integrated_result_round_trip_preserves_ir_bytes_provenance_and_identities(
    tmp_path,
):
    spec = BOUNDED_POOL_SCOPE_SPECS_V1[4]
    bundle, snapshot, bindings, result = _pool_evaluation((spec,))
    receipt = _selection_receipt(
        bundle, snapshot, result, result.shortlist[0].candidate_id
    )
    base_ir = build_frozen_realization_ir("P1", FROZEN_PROOF_CASES)
    ir = integrate_expression_selection_v1(
        base_ir=base_ir,
        eligibility_result=result,
        selection_receipt=receipt,
        relation_bindings=bindings,
        repetition_snapshot=snapshot,
    )
    output = render_integrated_expression_v1(
        ir=ir,
        eligibility_result=result,
        selection_receipt=receipt,
        relation_bindings=bindings,
        repetition_snapshot=snapshot,
    )
    artifact = finalize_integrated_expression_artifact_v1(
        IntegratedExpressionProofArtifactV1(
            ir=ir,
            result=output,
            selection_receipt=receipt,
            eligibility_result_identity=result.result_identity,
        )
    )
    store = IntegratedExpressionProofStoreV1(tmp_path / "proof.json")
    store.save(artifact)
    reloaded = store.load()
    assert reloaded == artifact
    assert reloaded.ir == ir
    assert reloaded.result.commentary_bytes == output.commentary_bytes
    assert reloaded.result.provenance == output.provenance
    assert reloaded.artifact_identity == artifact.artifact_identity
    assert reloaded.result.provenance[0].start == 0
    assert reloaded.result.provenance[-1].end == len(
        reloaded.result.commentary_bytes.decode("utf-8")
    )
    assert all(
        left.end == right.start
        for left, right in zip(
            reloaded.result.provenance,
            reloaded.result.provenance[1:],
            strict=False,
        )
    )
