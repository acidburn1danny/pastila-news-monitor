import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/production-core-semantic-adjudication-kit-v1.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_kit_authority_is_synthetic_candidate_neutral_and_component_bound():
    value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert value["status"] == "CANDIDATE_NEUTRAL_SYNTHETIC_ONLY_NOT_EXECUTION_AUTHORITY"
    assert value["adjudicator_roles"] == ["ADJUDICATOR_A", "ADJUDICATOR_B"]
    assert value["candidate_execution_authorized"] is False
    assert value["candidate_results_inspected"] is False
    assert value["candidate_promotion_effect"] is False
    assert value["public_key_registration"] == "SEPARATE_OWNER_AUTHORITY_REQUIRED"
    assert value["qualified_components"] == {
        "implementation_sha256": _sha(
            ROOT / "src/pastila_scout/production_core_semantic_adjudication_v1.py"
        ),
        "executable_test_sha256": _sha(
            ROOT / "tests/test_production_core_semantic_adjudication_v1.py"
        ),
        "documentation_sha256": _sha(
            ROOT / "docs/production-core-semantic-adjudication-kit-v1.md"
        ),
    }


def test_holdout_claim_is_project_scoped_and_global_exclusion_is_disclaimed():
    value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    holdout = value["project_controlled_true_holdout"]
    assert holdout["minimum_cases"] == 50
    assert holdout["freeze_before_candidate_evaluation"] is True
    assert holdout["separate_case_and_manifest_sha256"] is True
    assert len(holdout["excluded_project_activities"]) == 7
    assert (
        "GLOBAL_TRAINING_EXCLUSION is not claimed"
        in holdout["external_pretraining_disclaimer"]
    )


def test_artifact_contains_no_host_paths_or_private_key_material():
    raw = ARTIFACT.read_text(encoding="utf-8")
    assert "C:\\" not in raw and "/home/" not in raw
    assert "PRIVATE KEY" not in raw
