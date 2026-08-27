import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_controller_candidate_identity_sources_and_closed_authority():
    artifact = json.loads((ROOT / "docs" / "artifacts" /
        "semantic-admission-v2-stage-p-phase2-character-controller-liveness-v1.json"
    ).read_text(encoding="utf-8"))
    fields = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == artifact["canonical_identity"]
    source = ROOT / artifact["implementation"]["path"]
    assert _sha(source) == artifact["implementation"]["sha256"]
    bound_test = ROOT / "tests" / "test_semantic_admission_v2_stage_p_phase2_character_controller_v1.py"
    assert _sha(bound_test) in fields
    assert artifact["verification"]["inference_calls"] == 0
    assert not any(artifact["authority"].values())
    assert artifact["status"] == "OWNER_REVIEW_REQUIRED"


def test_both_dfa_freeze_receipts_rederive_and_preserve_authority_boundary():
    for name in (
        "semantic-admission-v2-stage-p-phase2-commitment-span-character-dfa-v1-freeze.json",
        "semantic-admission-v2-stage-p-phase2-authority-reconciliation-character-dfa-v1-freeze.json",
    ):
        receipt = json.loads((ROOT / "docs" / "artifacts" / name).read_text(encoding="utf-8"))
        fields = receipt["identity_derivation"]["ordered_utf8_fields"]
        assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == receipt["canonical_identity"]
        assert receipt["status"] == "FROZEN"
        assert not any(receipt["authority"].values())
