from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / ".semantic-admission-v2-staged-gate-f-coordinator-v1-evidence/manifest.json"
RECONCILIATION = ROOT / "docs/artifacts/semantic-admission-v2-staged-gate-f-coordinator-identity-reconciliation-v1.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_historical_identity_and_expected_source_hash_remain_immutable() -> None:
    manifest = json.loads(HISTORICAL.read_text("utf-8"))
    identity = hashlib.sha256(
        "\n".join(item["sha256"].lower() for item in manifest["artifacts"]).encode("ascii")
    ).hexdigest()
    assert identity == manifest["canonical_identity"] == "9d2f55be9771f0da0ab6a547217e8fc450167d30651bd12d7898fd36830a47bc"
    source = next(item for item in manifest["artifacts"] if item["path"].endswith("staged_gate_f_coordinator_v1.py"))
    assert source["sha256"] == "0ee8279f8ad7ecc2b372538597f47cd6084786cce1dba143e08e841b97558c5a"


def test_only_historical_source_hash_differs_and_other_artifacts_match() -> None:
    manifest = json.loads(HISTORICAL.read_text("utf-8"))
    mismatches = []
    for item in manifest["artifacts"]:
        if _sha(ROOT / item["path"]) != item["sha256"]:
            mismatches.append(item["path"])
    assert mismatches == ["src/pastila_scout/semantic_admission_v2/staged_gate_f_coordinator_v1.py"]


def test_current_source_and_provenance_are_bound_without_equivalence_claim() -> None:
    receipt = json.loads(RECONCILIATION.read_text("utf-8"))
    current = receipt["current_source"]
    assert _sha(ROOT / current["path"]) == current["sha256"] == "339ec6a6c5eddc26836f58cf19478df4cb7bc7bf8beb5e3cf8a159881ae3d82e"
    assert current["provenance_commit"] == "b449a8667f9e956eb74cecc1f91c6ac8d8149c0c"
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
