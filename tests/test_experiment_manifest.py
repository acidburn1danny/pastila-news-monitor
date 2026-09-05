"""Canonical controlled-experiment manifest contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.editor.generation.controlled_revision_quality.experiment_manifest import (
    ExperimentManifest,
    GateStatus,
    canonical_manifest_fingerprint,
    deserialize_manifest,
    json_schema,
    serialize_manifest,
    validate_manifest,
)
from scripts.build_experiment_manifest import (
    MANIFEST_PATH,
    build_part_7h2_manifest,
)

ROOT = Path.cwd()


def _manifest() -> ExperimentManifest:
    return build_part_7h2_manifest(ROOT)


def _dump() -> dict:
    return _manifest().model_dump(mode="json")


def _invalid(mutator) -> None:
    data = _dump()
    mutator(data)
    with pytest.raises(ValidationError):
        ExperimentManifest.model_validate(data)


def test_part_7h2_manifest_builds_and_validates():
    manifest = _manifest()
    diagnostics = validate_manifest(manifest, ROOT)

    assert diagnostics.status == GateStatus.PASS
    assert diagnostics.validated_artifacts == 9
    assert not diagnostics.errors


def test_serialization_and_deserialization_round_trip(tmp_path: Path):
    path = tmp_path / "manifest.json"
    manifest = _manifest()
    serialize_manifest(path, manifest)

    assert deserialize_manifest(path) == manifest
    assert path.read_bytes().endswith(b"\n")


def test_fingerprint_is_deterministic_and_ignores_json_formatting():
    first = _manifest()
    reformatted = json.loads(json.dumps(first.model_dump(mode="json"), indent=7))

    assert canonical_manifest_fingerprint(first) == canonical_manifest_fingerprint(
        reformatted
    )
    assert first.manifest.manifest_fingerprint == canonical_manifest_fingerprint(first)


def test_unsupported_schema_version_fails_closed():
    _invalid(lambda data: data["manifest"].update(schema_version="2.0.0"))


def test_missing_experiment_id_is_rejected():
    _invalid(lambda data: data["experiment"].pop("experiment_id"))


def test_missing_baseline_fingerprint_is_rejected():
    _invalid(lambda data: data["baseline"].pop("prompt_fingerprint"))


def test_missing_treatment_fingerprint_is_rejected():
    _invalid(lambda data: data["treatment"].pop("prompt_fingerprint"))


def test_invalid_controlled_vocabulary_is_rejected():
    _invalid(lambda data: data["experiment"].update(experiment_type="UNCONTROLLED"))


def test_missing_required_artifact_is_detected():
    manifest = _manifest()
    artifact = manifest.artifacts[0].model_copy(
        update={"artifact_path": "docs/artifacts/does-not-exist.json"}
    )
    changed = manifest.model_copy(
        update={"artifacts": [artifact, *manifest.artifacts[1:]]}
    )

    assert validate_manifest(changed, ROOT).status == GateStatus.FAIL
    assert "missing required artifact" in validate_manifest(changed, ROOT).errors[1]


def test_tampered_artifact_fingerprint_is_detected():
    manifest = _manifest()
    artifact = manifest.artifacts[0].model_copy(update={"fingerprint": "0" * 64})
    changed = manifest.model_copy(
        update={"artifacts": [artifact, *manifest.artifacts[1:]]}
    )

    diagnostics = validate_manifest(changed, ROOT)
    assert diagnostics.status == GateStatus.FAIL
    assert any("artifact fingerprint mismatch" in item for item in diagnostics.errors)


def test_scenario_count_mismatch_is_rejected():
    _invalid(lambda data: data["benchmark"].update(scenario_count=23))


def test_provider_request_count_mismatch_is_rejected():
    _invalid(lambda data: data["execution"]["actual"].update(provider_responses=23))


def test_editorial_total_mismatch_is_rejected():
    _invalid(
        lambda data: data["results"]["editorial"].update(
            editorial_acceptance_failures=23
        )
    )


def test_technical_total_mismatch_is_rejected():
    _invalid(
        lambda data: data["results"]["technical"].update(technical_pipeline_failures=1)
    )


def test_reference_total_mismatch_is_rejected():
    _invalid(
        lambda data: data["results"]["reference"].update(
            exact_reference_compliance_total=23
        )
    )


def test_invalid_candidate_decision_is_rejected():
    _invalid(lambda data: data["decision"].update(candidate_decision="MAYBE"))


def test_reject_with_production_promotion_is_rejected():
    _invalid(lambda data: data["promotion"].update(production_promotion=True))


@pytest.mark.parametrize(
    "gate",
    ["technical_non_regression", "reference_non_regression", "editorial_improvement"],
)
def test_adopt_with_failed_gate_is_rejected(gate: str):
    def mutate(data):
        data["decision"]["candidate_decision"] = "ADOPT"
        data["decision"]["root_conclusion"] = "H2_PROMPT_EFFECTIVE"
        data["results"][
            (
                "technical"
                if gate == "technical_non_regression"
                else "reference" if gate == "reference_non_regression" else "editorial"
            )
        ][gate] = "FAIL"

    _invalid(mutate)


def test_budget_exceeded_with_pass_status_is_rejected():
    def mutate(data):
        data["prompt_delta_budget"]["budget_consumed"] = 2
        data["prompt_delta_budget"]["budget_exceeded"] = True
        data["prompt_delta_budget"]["validation_status"] = "PASS"

    _invalid(mutate)


def test_equal_prompt_fingerprints_are_rejected_for_prompt_experiment():
    _invalid(
        lambda data: data["treatment"].update(
            prompt_fingerprint=data["baseline"]["prompt_fingerprint"]
        )
    )


def test_inconsistent_root_conclusion_is_rejected():
    _invalid(
        lambda data: data["decision"].update(root_conclusion="H2_PROMPT_EFFECTIVE")
    )


def test_lineage_references_all_required_milestones():
    manifest = _manifest()

    assert [item.milestone for item in manifest.lineage] == [
        "Part 7C.2",
        "Part 7C.2.1",
        "Part 7H",
        "Part 7H.1",
        "Part 7H.2",
    ]
    assert all(item.required for item in manifest.lineage)


def test_part_7h2_decision_semantics_are_preserved():
    manifest = _manifest()

    assert manifest.results.technical.technical_non_regression == GateStatus.PASS
    assert manifest.results.reference.reference_non_regression == GateStatus.PASS
    assert manifest.results.editorial.editorial_improvement == GateStatus.FAIL
    assert manifest.decision.candidate_decision == "REJECT"
    assert manifest.decision.root_conclusion == "H2_PROMPT_INEFFECTIVE"
    assert manifest.promotion.production_promotion is False


def test_manifest_contains_no_secrets_or_absolute_user_paths():
    text = json.dumps(_dump(), ensure_ascii=False).casefold()

    for forbidden in (
        "api_key",
        "access_token",
        "authorization_header",
        "bearer ",
        "credentials",
        "c:\\users\\",
    ):
        assert forbidden not in text


def test_json_schema_is_versioned_and_checked_in():
    schema = json_schema()
    checked_in = json.loads(
        Path("docs/schemas/experiment-manifest.schema.json").read_text(encoding="utf-8")
    )

    assert schema == checked_in
    assert schema["title"] == "ExperimentManifest"


def test_checked_in_historical_manifest_preserves_its_history_link():
    checked_in = deserialize_manifest(MANIFEST_PATH)
    history = json.loads(
        Path("docs/artifacts/controlled-provider-quality-history.json").read_text(
            encoding="utf-8"
        )
    )["history"][-1]

    assert history["manifest_path"] == MANIFEST_PATH.as_posix()
    assert history["manifest_fingerprint"] == checked_in.manifest.manifest_fingerprint
    assert history["manifest_validation_status"] == "PASS"
