import hashlib
import json
from pathlib import Path

from scripts.run_semantic_admission_v2_ten_case_conformance_v1 import preflight_payload

ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = (
    ROOT
    / ".humor-mechanics-curriculum-v1-semantic-admission-specificity-contrast-pack-v1-evidence"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_ten_case_payload_is_complete_and_non_authorizing():
    payload = preflight_payload()
    contract = payload["contract"]

    assert payload["stage0_1_identity"] == (
        "160e62594ca30b15f69a35a8003b6f2c46edc8e4faf07a497857c69b40a58c32"
    )
    assert len(payload["cases"]) == len(payload["attempts"]) == 10
    assert list(payload["cases"]) == contract["case_ids"]
    assert contract["attempts_per_case_per_gate"] == 1
    assert contract["silent_retry"] is False
    assert contract["repair"] is False
    assert contract["selection"] is False
    assert contract["inference_authorized_by_this_contract"] is False


def test_source_pack_and_owner_closure_hashes_rederive():
    pack = json.loads((PACK_ROOT / "pack-manifest.json").read_text("utf-8"))
    final = json.loads((PACK_ROOT / "final-manifest.json").read_text("utf-8"))
    closure = json.loads(
        (PACK_ROOT / "owner-adjudication-closure-manifest.json").read_text("utf-8")
    )

    assert _sha(PACK_ROOT / "generation-pack.json") == pack["generation_pack_sha256"]
    assert (
        _sha(PACK_ROOT / "hidden-evaluation-key.json")
        == pack["hidden_evaluation_key_sha256"]
    )
    assert (
        _sha(ROOT / "scripts/build_semantic_admission_specificity_contrast_pack_v1.py")
        == pack["builder_script_sha256"]
    )
    assert _sha(PACK_ROOT / "raw-run-results.json") == final["raw_run_results_sha256"]
    assert (
        _sha(PACK_ROOT / "evaluation-results.json")
        == final["evaluation_results_sha256"]
    )
    assert (
        _sha(PACK_ROOT / "owner-adjudicated-baseline.json")
        == closure["owner_adjudicated_baseline_sha256"]
    )
    assert closure["source_final_evidence_identity"] == final["canonical_identity"]
    assert closure["curriculum_authority"] is False
    assert closure["runtime_authority"] is False
