from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / ".semantic-admission-v2-stage-p-role-coherence-v2-binding-evidence/manifest.json"
RECONCILIATION = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-role-coherence-v2-binding-identity-reconciliation-v1.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_historical_manifest_identity_remains_immutable() -> None:
    manifest = json.loads(HISTORICAL.read_text("utf-8"))
    values = [manifest["source_projection_identity"]]
    values.extend(item["sha256"].lower() for item in manifest["bindings"])
    identity = hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()
    assert identity == manifest["canonical_identity"] == "c00901f681153fc6b4529d1d4600629628615baac58da8310fa76f4c3353d94d"


def test_only_the_three_recorded_historical_sources_differ() -> None:
    manifest = json.loads(HISTORICAL.read_text("utf-8"))
    mismatches = [item["path"] for item in manifest["bindings"] if _sha(ROOT / item["path"]) != item["sha256"]]
    assert mismatches == [
        "docs/artifacts/semantic-admission-v2-stage-p-role-coherence-v2-binding-candidate.json",
        "src/pastila_scout/semantic_admission_v2/stage_p_role_coherence_candidate_v2.py",
        "tests/test_semantic_admission_v2_stage_p_role_coherence_v2_binding.py",
    ]


def test_current_sources_and_provenance_are_bound_without_equivalence_claim() -> None:
    receipt = json.loads(RECONCILIATION.read_text("utf-8"))
    for item in receipt["unavailable_historical_sources"]:
        assert _sha(ROOT / item["path"]) == item["current_sha256"]
        assert item["expected_sha256"] != item["current_sha256"]
        assert item["current_provenance_commit"] == "fb3b265264ef973aaf15b84fde27eaf87797bd6f"
        assert item["expected_bytes_available_from_git"] is False
        assert item["expected_bytes_available_from_repository_content"] is False
    distinction = receipt["identity_distinction"]
    assert distinction["byte_equivalence_claimed"] is False
    assert distinction["semantic_equivalence_claimed"] is False
    assert distinction["silent_hash_rebinding"] is False


def test_reconciliation_identity_is_canonical_and_separate() -> None:
    receipt = json.loads(RECONCILIATION.read_text("utf-8"))
    claimed = receipt.pop("reconciliation_identity")
    payload = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    assert claimed == "sha256:" + hashlib.sha256(payload).hexdigest()
    assert claimed.removeprefix("sha256:") != receipt["historical_bundle"]["canonical_identity"]


def test_reconciliation_grants_no_execution_or_runtime_authority() -> None:
    receipt = json.loads(RECONCILIATION.read_text("utf-8"))
    assert all(value is False for value in receipt["authority"].values())
    assert receipt["availability_audit"]["reconstruction_or_fabrication_permitted"] is False
