import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs" / "artifacts"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(name: str):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def _identity(artifact) -> str:
    fields = artifact["identity_derivation"]["ordered_utf8_fields"]
    return hashlib.sha256("\n".join(fields).encode("utf-8")).hexdigest()


def test_approved_prompt_request_candidate_is_frozen_without_expanded_authority():
    receipt = _load(
        "semantic-admission-v2-stage-p-phase2-prompt-request-candidates-v1-freeze.json"
    )
    assert _identity(receipt) == receipt["canonical_identity"]
    assert receipt["frozen_candidate_identity"] == (
        "57a23e50670deae55efd8e2d3c245314dfa4c205e4fc1a1e6de1d969ec25c698"
    )
    assert receipt["status"] == "FROZEN"
    assert not any(receipt["authority"].values())


def test_both_character_dfa_artifacts_are_identity_and_source_bound():
    source = ROOT / "src" / "pastila_scout" / "semantic_admission_v2" / (
        "stage_p_phase2_character_dfa_v1.py"
    )
    test_source = ROOT / "tests" / (
        "test_semantic_admission_v2_stage_p_phase2_character_dfa_v1.py"
    )
    for name in (
        "semantic-admission-v2-stage-p-phase2-commitment-span-character-dfa-v1.json",
        "semantic-admission-v2-stage-p-phase2-authority-reconciliation-character-dfa-v1.json",
    ):
        artifact = _load(name)
        assert _identity(artifact) == artifact["canonical_identity"]
        assert artifact["implementation"]["sha256"] == _sha(source)
        assert artifact["identity_derivation"]["ordered_utf8_fields"].count(_sha(test_source)) == 1
        assert artifact["verification"]["inference_calls"] == 0
        assert not any(artifact["authority"].values())
        assert artifact["status"] == "OWNER_REVIEW_REQUIRED"
