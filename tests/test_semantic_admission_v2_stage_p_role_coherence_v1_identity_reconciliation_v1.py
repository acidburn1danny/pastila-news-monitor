from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / ".semantic-admission-v2-stage-p-role-coherence-v1-evidence/manifest.json"
RECONCILIATION = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-role-coherence-v1-identity-reconciliation-v1.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_historical_manifest_identity_and_expected_source_remain_immutable() -> None:
    manifest = json.loads(HISTORICAL.read_text("utf-8"))
    values = [manifest["source_design_identity"]]
    values.extend(item["sha256"].lower() for item in manifest["bindings"])
    assert hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest() == manifest["canonical_identity"]
    assert manifest["canonical_identity"] == "03012d7a499634d884581aa4885bf951ff0f815176cbf04f457537ac621c9d4e"


def test_only_historical_candidate_source_hash_differs() -> None:
    manifest = json.loads(HISTORICAL.read_text("utf-8"))
    mismatches = [item["path"] for item in manifest["bindings"] if _sha(ROOT / item["path"]) != item["sha256"]]
    assert mismatches == ["src/pastila_scout/semantic_admission_v2/stage_p_role_coherence_candidate_v1.py"]


def test_current_source_and_provenance_are_bound_without_equivalence_claim() -> None:
    receipt = json.loads(RECONCILIATION.read_text("utf-8"))
    current = receipt["current_source"]
    assert _sha(ROOT / current["path"]) == current["sha256"] == "3ea430789466c53f0565320c5ce5ccec15677e4797392502b893269bdb580e98"
    assert current["provenance_commit"] == "d34ab6a4ea6a1f2bfd588558892fc3f108c672a9"
    distinction = receipt["identity_distinction"]
    assert distinction["byte_equivalence_claimed"] is False
    assert distinction["semantic_equivalence_claimed"] is False
    assert distinction["silent_hash_rebinding"] is False


def test_reconciliation_identity_is_canonical_and_new() -> None:
    receipt = json.loads(RECONCILIATION.read_text("utf-8"))
    claimed = receipt.pop("reconciliation_identity")
    payload = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    assert claimed == "sha256:" + hashlib.sha256(payload).hexdigest()
    assert claimed.removeprefix("sha256:") != receipt["historical_bundle"]["canonical_identity"]


def test_reconciliation_grants_no_execution_or_runtime_authority() -> None:
    receipt = json.loads(RECONCILIATION.read_text("utf-8"))
    assert all(value is False for value in receipt["authority"].values())
    assert receipt["legacy_source_availability"]["reconstruction_or_fabrication_permitted"] is False
