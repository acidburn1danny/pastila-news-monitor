"""Focused contract and safety tests for Module 2.3."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.editor.decision import (
    CANONICAL_DECISION_RULES,
    CoreElement,
    DecisionConfidence,
    DecisionStage,
    DecisionValidationError,
    EditorialAction,
    EditorialCore,
    EditorialDecision,
    EditorialDecisionPlan,
    EditorialMaterial,
    EditorialRisk,
    FactImportance,
    FactualStatus,
    MaterialType,
    ProductionReadiness,
    RiskSeverity,
    RiskType,
    decision_plan_fingerprint,
    render_decision_plan,
    source_material_fingerprint,
    validate_decision_plan,
)
from pastila_scout.editor.decision.models import MaterialMetadata
from pastila_scout.editor.persona import DEFAULT_EDITORIAL_PERSONA


def _materials() -> tuple[EditorialMaterial, ...]:
    return (
        EditorialMaterial(
            material_id="m1",
            source_reference="source-a",
            material_type=MaterialType.FACT,
            content="Consiliul a aprobat măsura miercuri.",
            factual_status=FactualStatus.VERIFIED_FACT,
            chronology_position=1,
            metadata=(MaterialMetadata(key="region", value="București"),),
        ),
        EditorialMaterial(
            material_id="m2",
            source_reference="source-b",
            material_type=MaterialType.ALLEGATION,
            content="Un martor susține că procedura nu a fost respectată.",
            factual_status=FactualStatus.ALLEGATION,
            attribution="martor citat de source-b",
            chronology_position=2,
        ),
        EditorialMaterial(
            material_id="m3",
            source_reference="source-c",
            material_type=MaterialType.QUOTE,
            content="Am urmat procedura, a declarat instituția.",
            factual_status=FactualStatus.ATTRIBUTED_CLAIM,
            attribution="instituția",
            chronology_position=3,
        ),
    )


def _core() -> EditorialCore:
    return EditorialCore(
        what_happened=CoreElement(
            statement="Măsura a fost aprobată.", material_ids=("m1",)
        ),
        involved_parties=CoreElement(
            statement="Consiliul și instituția.", material_ids=("m1", "m3")
        ),
        why_it_matters=CoreElement(
            statement="Procedura este contestată.", material_ids=("m2", "m3")
        ),
        consequence=CoreElement(
            statement="Decizia afectează publicul.", material_ids=("m1",)
        ),
        central_tension=CoreElement(
            statement="Aprobare versus procedură.", material_ids=("m1", "m2")
        ),
        factual_boundaries=(
            CoreElement(
                statement="Contestația rămâne o afirmație atribuită.",
                material_ids=("m2",),
            ),
        ),
        unresolved_questions=("Există documente suplimentare?",),
    )


def _decision(**changes) -> EditorialDecision:
    values = {
        "decision_id": "d1",
        "stage": DecisionStage.INDISPENSABLE_FACTS,
        "rank": 1,
        "material_ids": ("m1",),
        "classification": FactImportance.INDISPENSABLE,
        "action": EditorialAction.PRESERVE,
        "rationale": "The verified central fact establishes what happened.",
        "evidence": ("m1",),
        "principle_ids": ("truth-before-performance",),
        "tension_ids": ("clarity-versus-completeness",),
        "confidence": DecisionConfidence.HIGH,
        "consequence_if_ignored": "The account would become materially incomplete.",
    }
    values.update(changes)
    return EditorialDecision(**values)


def _plan(**changes) -> EditorialDecisionPlan:
    materials = changes.pop("source_material", _materials())
    values = {
        "plan_id": "plan-1",
        "version": "1.0.0",
        "persona_id": DEFAULT_EDITORIAL_PERSONA.persona_id,
        "persona_version": DEFAULT_EDITORIAL_PERSONA.version,
        "philosophy_id": DEFAULT_EDITORIAL_PERSONA.philosophy.philosophy_id,
        "philosophy_version": DEFAULT_EDITORIAL_PERSONA.philosophy.version,
        "source_material_fingerprint": source_material_fingerprint(materials),
        "source_material": materials,
        "editorial_core": _core(),
        "decisions": (_decision(),),
        "requires_editor_in_chief_review": False,
        "production_readiness": ProductionReadiness.READY,
        "summary": "Evidence-linked assessment only.",
    }
    values.update(changes)
    return EditorialDecisionPlan(**values)


def test_canonical_models_are_immutable():
    with pytest.raises(ValidationError):
        _plan().summary = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("model", "field", "value"),
    [
        (EditorialMaterial, "material_type", "invented"),
        (EditorialMaterial, "factual_status", "certain"),
        (EditorialDecision, "classification", "vital"),
        (EditorialDecision, "action", "rewrite"),
        (EditorialDecision, "confidence", "certain"),
        (EditorialRisk, "severity", "urgent"),
        (EditorialDecisionPlan, "production_readiness", "publish"),
    ],
)
def test_constrained_enums_reject_invalid_values(model, field, value):
    source = {
        EditorialMaterial: _materials()[0],
        EditorialDecision: _decision(),
        EditorialRisk: EditorialRisk(
            risk_id="r1",
            risk_type=RiskType.PACING_LOSS,
            severity=RiskSeverity.LOW,
            affected_material_ids=("m1",),
            explanation="Long context.",
            mitigation="Compress safely.",
            blocking=False,
            requires_editor_in_chief_review=False,
        ),
        EditorialDecisionPlan: _plan(),
    }[model]
    data = source.model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        model.model_validate(data)


def test_valid_material_collection_and_plan_validate():
    assert validate_decision_plan(_plan(), DEFAULT_EDITORIAL_PERSONA) == _plan()
    assert len(CANONICAL_DECISION_RULES) == 25


def test_duplicate_material_identifiers_are_rejected():
    materials = (*_materials(), _materials()[0])
    plan = _plan(source_material=materials)
    with pytest.raises(DecisionValidationError, match="duplicate material"):
        validate_decision_plan(plan, DEFAULT_EDITORIAL_PERSONA)


def test_decision_referencing_unknown_material_is_rejected():
    plan = _plan(decisions=(_decision(material_ids=("missing",)),))
    with pytest.raises(DecisionValidationError, match="unknown material"):
        validate_decision_plan(plan, DEFAULT_EDITORIAL_PERSONA)


def test_editorial_core_referencing_unknown_evidence_is_rejected():
    core = _core().model_copy(
        update={"what_happened": CoreElement(statement="Unknown.", material_ids=("x",))}
    )
    with pytest.raises(DecisionValidationError, match="core references unknown"):
        validate_decision_plan(_plan(editorial_core=core), DEFAULT_EDITORIAL_PERSONA)


def test_indispensable_fact_cannot_be_removed():
    plan = _plan(decisions=(_decision(action=EditorialAction.REMOVE),))
    with pytest.raises(DecisionValidationError, match="cannot be removed"):
        validate_decision_plan(plan, DEFAULT_EDITORIAL_PERSONA)


def test_allegation_cannot_silently_become_verified_fact():
    items = list(_materials())
    items[1] = items[1].model_copy(
        update={"factual_status": FactualStatus.VERIFIED_FACT}
    )
    plan = _plan(
        source_material=tuple(items),
        decisions=(_decision(material_ids=("m2",)),),
    )
    with pytest.raises(DecisionValidationError, match="without evidence"):
        validate_decision_plan(plan, DEFAULT_EDITORIAL_PERSONA)


def test_disputed_claim_requires_attribution():
    items = list(_materials())
    items[1] = items[1].model_copy(
        update={"factual_status": FactualStatus.DISPUTED_CLAIM, "attribution": None}
    )
    plan = _plan(
        source_material=tuple(items), decisions=(_decision(material_ids=("m2",)),)
    )
    with pytest.raises(DecisionValidationError, match="require attribution"):
        validate_decision_plan(plan, DEFAULT_EDITORIAL_PERSONA)


def test_unresolved_claim_can_be_held_for_verification():
    items = list(_materials())
    items[1] = items[1].model_copy(
        update={"factual_status": FactualStatus.UNKNOWN_UNRESOLVED}
    )
    decision = _decision(
        material_ids=("m2",),
        classification=FactImportance.UNRESOLVED,
        action=EditorialAction.HOLD_FOR_VERIFICATION,
    )
    assert validate_decision_plan(
        _plan(source_material=tuple(items), decisions=(decision,)),
        DEFAULT_EDITORIAL_PERSONA,
    )


def test_compression_must_preserve_attribution():
    decision = _decision(
        material_ids=("m2",),
        action=EditorialAction.COMPRESS,
        preserves_attribution=False,
    )
    with pytest.raises(DecisionValidationError, match="preserve attribution"):
        validate_decision_plan(_plan(decisions=(decision,)), DEFAULT_EDITORIAL_PERSONA)


def test_contradictory_claims_cannot_be_merged_as_one_fact():
    decision = _decision(
        material_ids=("m2", "m3"),
        action=EditorialAction.COMBINE,
        merges_contradictory_claims=True,
    )
    with pytest.raises(DecisionValidationError, match="contradictory claims"):
        validate_decision_plan(_plan(decisions=(decision,)), DEFAULT_EDITORIAL_PERSONA)


def test_quote_mutation_is_rejected():
    decision = _decision(material_ids=("m3",), mutates_quote=True)
    with pytest.raises(DecisionValidationError, match="quote mutation"):
        validate_decision_plan(_plan(decisions=(decision,)), DEFAULT_EDITORIAL_PERSONA)


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("infers_unsupported_motive", "motive inference"),
        ("infers_unsupported_causality", "causal inference"),
        ("silently_removes_uncertainty", "uncertainty"),
    ],
)
def test_unsupported_inference_and_uncertainty_removal_are_rejected(field, message):
    with pytest.raises(DecisionValidationError, match=message):
        validate_decision_plan(
            _plan(decisions=(_decision(**{field: True}),)),
            DEFAULT_EDITORIAL_PERSONA,
        )


@pytest.mark.parametrize("purpose", ["pacing", "satire", "retention"])
def test_factual_distortion_is_rejected_for_every_editorial_purpose(purpose):
    with pytest.raises(DecisionValidationError, match="factual distortion"):
        validate_decision_plan(
            _plan(decisions=(_decision(factual_distortion_purpose=purpose),)),
            DEFAULT_EDITORIAL_PERSONA,
        )


def _risk(severity=RiskSeverity.LOW, blocking=False, review=False) -> EditorialRisk:
    return EditorialRisk(
        risk_id="r1",
        risk_type=RiskType.INSUFFICIENT_VERIFICATION,
        severity=severity,
        affected_material_ids=("m1",),
        explanation="Verification remains incomplete.",
        mitigation="Verify before production.",
        blocking=blocking,
        requires_editor_in_chief_review=review,
    )


def test_critical_risk_produces_blocked_readiness():
    plan = _plan(risks=(_risk(RiskSeverity.CRITICAL),), production_readiness="blocked")
    assert validate_decision_plan(plan, DEFAULT_EDITORIAL_PERSONA)


def test_editor_review_requirement_produces_review_readiness():
    plan = _plan(
        decisions=(_decision(requires_editor_in_chief_review=True),),
        requires_editor_in_chief_review=True,
        production_readiness="requires_editor_review",
    )
    assert validate_decision_plan(plan, DEFAULT_EDITORIAL_PERSONA)


def test_advisory_produces_ready_with_advisories():
    plan = _plan(
        advisory_issues=("Watch pacing.",), production_readiness="ready_with_advisories"
    )
    assert validate_decision_plan(plan, DEFAULT_EDITORIAL_PERSONA)


def test_clean_plan_is_ready():
    assert _plan().production_readiness == ProductionReadiness.READY
    assert validate_decision_plan(_plan(), DEFAULT_EDITORIAL_PERSONA)


@pytest.mark.parametrize(
    "changes",
    [
        {"blocking_issues": ("Missing central evidence.",)},
        {"advisory_issues": ("Watch pacing.",)},
    ],
)
def test_ready_cannot_coexist_with_blockers_or_advisories(changes):
    with pytest.raises(DecisionValidationError, match="production readiness"):
        validate_decision_plan(_plan(**changes), DEFAULT_EDITORIAL_PERSONA)


def test_known_and_unknown_principle_references():
    assert validate_decision_plan(_plan(), DEFAULT_EDITORIAL_PERSONA)
    with pytest.raises(DecisionValidationError, match="unknown principle"):
        validate_decision_plan(
            _plan(decisions=(_decision(principle_ids=("invented",)),)),
            DEFAULT_EDITORIAL_PERSONA,
        )


def test_known_and_unknown_tension_references():
    assert validate_decision_plan(_plan(), DEFAULT_EDITORIAL_PERSONA)
    with pytest.raises(DecisionValidationError, match="unknown tension"):
        validate_decision_plan(
            _plan(decisions=(_decision(tension_ids=("invented",)),)),
            DEFAULT_EDITORIAL_PERSONA,
        )


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("persona_version", "Persona version"),
        ("philosophy_version", "philosophy version"),
    ],
)
def test_persona_and_philosophy_version_mismatch_is_rejected(field, message):
    with pytest.raises(DecisionValidationError, match=message):
        validate_decision_plan(_plan(**{field: "9.0.0"}), DEFAULT_EDITORIAL_PERSONA)


def test_deterministic_rendering_uses_explicit_order_and_all_sections():
    second = _decision(decision_id="d2", stage=DecisionStage.FACTUAL_SAFETY, rank=1)
    plan = _plan(decisions=(_decision(), second))
    first = render_decision_plan(plan, DEFAULT_EDITORIAL_PERSONA)
    second_render = render_decision_plan(plan, DEFAULT_EDITORIAL_PERSONA)
    assert first.encode("utf-8") == second_render.encode("utf-8")
    assert first.index("- d2") < first.index("- d1")
    for section in (
        "Plan Identity",
        "Production Readiness",
        "Editorial Core",
        "Material Assessment",
        "Editorial Decisions",
        "Editorial Risks",
        "Unresolved Questions",
        "Blocking Issues",
        "Advisory Issues",
        "Editor-in-Chief Review",
    ):
        assert f"\n{section}\n" in first


def test_renderer_reproduces_material_without_rewriting():
    rendered = render_decision_plan(_plan(), DEFAULT_EDITORIAL_PERSONA)
    assert all(item.content in rendered for item in _materials())


def test_source_material_fingerprint_is_deterministic_and_order_neutral():
    assert source_material_fingerprint(_materials()) == source_material_fingerprint(
        tuple(reversed(_materials()))
    )


def test_decision_plan_fingerprint_is_deterministic():
    assert decision_plan_fingerprint(_plan()) == decision_plan_fingerprint(_plan())


def test_meaningful_material_and_chronology_changes_alter_fingerprint():
    items = list(_materials())
    items[0] = items[0].model_copy(update={"content": "Alt fapt."})
    assert source_material_fingerprint(items) != source_material_fingerprint(
        _materials()
    )
    items = list(_materials())
    items[0] = items[0].model_copy(update={"chronology_position": 9})
    assert source_material_fingerprint(items) != source_material_fingerprint(
        _materials()
    )


def test_meaningful_decision_change_alters_plan_fingerprint():
    changed = _plan(decisions=(_decision(rationale="Different rationale."),))
    assert decision_plan_fingerprint(changed) != decision_plan_fingerprint(_plan())


def test_metadata_order_does_not_alter_material_fingerprint():
    items = list(_materials())
    items[0] = items[0].model_copy(
        update={
            "metadata": (
                MaterialMetadata(key="z", value="2"),
                MaterialMetadata(key="a", value="1"),
            )
        }
    )
    reversed_metadata = list(items)
    reversed_metadata[0] = items[0].model_copy(
        update={"metadata": tuple(reversed(items[0].metadata))}
    )
    assert source_material_fingerprint(items) == source_material_fingerprint(
        reversed_metadata
    )


def test_decision_package_has_no_forbidden_dependency():
    root = Path("src/pastila_scout/editor/decision")
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(root.glob("*.py"))
    ).casefold()
    for forbidden in (
        "import httpx",
        "import openai",
        "pastila_scout.ai",
        "pastila_scout.database",
        "pastila_scout.cli",
        "pastila_scout.editor.generation",
        "controlled_revision_quality",
        "path.write_text",
    ):
        assert forbidden not in source
